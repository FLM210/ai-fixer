# 架构设计

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        飞书群聊                              │
│   告警消息 → 机器人检测 → LLM 处理 → 结果卡片回复            │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                    ai-fixer 后端                             │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ 飞书模块  │  │ LangGraph    │  │ 插件系统              │  │
│  │ 消息检测  │  │ 工作流引擎    │  │ K8s/DB/Monitor/Shell  │  │
│  │ 卡片发送  │  │ 10 节点状态机 │  │ 27+ 内置插件          │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ LLM 层   │  │ 配置系统      │  │ 可观测性              │  │
│  │ Anthropic │  │ 环境变量+DB  │  │ Prometheus/OTEL       │  │
│  │ OpenAI   │  │ 动态热更新    │  │ structlog             │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    数据层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PostgreSQL   │  │ Redis        │  │ pgvector         │  │
│  │ 状态持久化    │  │ 锁/去重      │  │ 向量记忆         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## LangGraph 工作流

12 节点状态机，处理告警的完整生命周期:

```
ingest → triage → diagnose → await_diagnosis_approval → propose → policy_evaluate → await_proposal_approval → execute → verify → resolve/escalate
```

### 节点说明

| 节点 | 职责 | LLM 调用 |
|------|------|----------|
| `ingest` | 创建 Incident，检查重复 | 否 |
| `triage` | 分类（类别、严重程度、服务） | 1 次 |
| `diagnose` | 两阶段诊断（初步分析 + 工具排查） | 1-16 次 |
| `await_diagnosis_approval` | 发送诊断确认卡片，等待用户确认 | 否 |
| `propose` | 生成修复方案 | 1 次 |
| `policy_evaluate` | 策略评估（安全围栏） | 否 |
| `await_proposal_approval` | 发送方案确认卡片，等待用户确认 | 否 |
| `execute` | 执行修复操作 | 否 |
| `verify` | 验证修复结果 | 否 |
| `resolve` | 标记解决 | 否 |
| `escalate` | 升级处理 | 否 |

### 两步人工确认机制

工作流使用 LangGraph `interrupt/resume` 实现两步人工确认:

```
                          用户确认                  用户确认
diagnose ──────────→ [诊断确认卡片] ────→ propose ────→ [方案确认卡片] ────→ execute
                     (interrupt)          (resume)       (interrupt)          (resume)
```

**确认流程:**

1. `diagnose` 节点完成后进入 `await_diagnosis_approval`
2. 节点通过飞书 API 发送诊断确认卡片（含诊断结论、置信度、关键证据）
3. 调用 `interrupt()` 暂停工作流，状态保存到 checkpointer
4. `WorkflowRunManager` 注册 pending run，等待用户操作
5. 用户点击卡片按钮 → `/lark/card/action` 回调 → `workflow_manager.resume()`
6. 确认后工作流继续到 `propose` → `policy_evaluate` → `await_proposal_approval`
7. 再次 interrupt，发送方案确认卡片（含方案详情、风险等级）
8. 用户确认后执行修复

**关键模块:**

| 模块 | 文件 | 职责 |
|------|------|------|
| `WorkflowRunManager` | `app/lark/workflow_manager.py` | 管理 pending run，支持 resume 和超时清理 (1h) |
| `workflow_runner` | `app/lark/workflow_runner.py` | 公共逻辑：状态构建、结果保存、checkpointer 工厂 |
| `await_diagnosis_approval` | `app/graph/nodes/await_diagnosis_approval.py` | 诊断确认节点，发送卡片并 interrupt |
| `await_proposal_approval` | `app/graph/nodes/await_proposal_approval.py` | 方案确认节点，发送卡片并 interrupt |

**Checkpointer 策略:**

- 生产环境：`AsyncPostgresSaver`（PostgreSQL 持久化，进程重启不丢失）
- 开发环境：`MemorySaver`（内存存储，轻量快速）
- 由 `workflow_runner.create_checkpointer()` 工厂方法自动选择

### 两阶段诊断

```
阶段1: 无工具初步分析
  │
  ├─ 置信度 ≥ 0.7 → 直接出结论
  │
  └─ 置信度 < 0.7 → 阶段2: 工具排查
       │
       ├─ 根据类别选择相关工具（最多6个）
       │
       └─ LLM 调用工具 → 执行 → 返回结果 → 循环
```

### 条件边

| 条件 | 走向 |
|------|------|
| 重复告警 | → END |
| 无修复方案 | → resolve |
| 置信度 < 0.3 | → escalate |
| 全部 auto_execute | → execute（跳过审批） |
| 有需审批操作 | → await_proposal_approval |
| 诊断确认拒绝 | → escalate |
| 方案确认拒绝 | → escalate |
| 执行全部成功 | → verify |
| 执行部分成功 | → propose（重新诊断） |
| 执行全部失败 | → escalate |

## 数据模型

### 核心表

```
incidents
├── id (UUID PK)
├── fingerprint (去重指纹)
├── status (new/diagnosing/awaiting_approval/executing/resolved/escalated)
├── category, severity, service
├── summary, raw_alert
└── created_at, updated_at, resolved_at

diagnoses
├── incident_id (FK)
├── root_cause
├── confidence
└── evidence (JSONB)

fix_proposals
├── incident_id (FK)
├── plugin_name, args, risk_level
└── description, expected_outcome

fix_executions
├── incident_id (FK), proposal_id (FK)
├── status, output, error
└── approved_by, started_at, finished_at

llm_turns
├── incident_id (FK)
├── phase (triage/diagnose/propose)
├── turn_index, role, content
└── tool_name, tool_input

system_configs
├── key (PK)
├── value, value_type
└── updated_at, updated_by

environment_context
├── id (PK)
├── content
└── updated_at, updated_by
```

## 插件系统

### 注册流程

```python
@register(global_registry)
class MyPlugin(Plugin):
    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="custom.my_plugin",
            category="diagnostic",
            ...
        )

    async def execute(self, ctx, args) -> PluginResult:
        ...
```

### 加载顺序

1. 启动时从数据库加载 `disabled_plugins` 列表
2. 扫描 `app/plugins/builtin/` 目录
3. 扫描 `custom_plugins/` 目录
4. 应用禁用状态

### 热重载

```
POST /api/plugins/reload
  │
  ├─ 清空注册表
  │
  ├─ 重新扫描 builtin/ 目录
  │
  ├─ 重新扫描 custom_plugins/ 目录
  │
  └─ 应用禁用状态
```

## 配置系统

### 两层架构

```
┌─────────────────────────────────┐
│         前端管理页面              │
│  GET/PUT /api/config             │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│       DynamicConfig              │
│  内存缓存 + DB 持久化            │
│  system_configs 表               │
└──────────────┬──────────────────┘
               │ 优先级: DB > Env
┌──────────────▼──────────────────┐
│        Settings (Pydantic)       │
│  .env 文件加载                   │
│  @lru_cache 单例                 │
└─────────────────────────────────┘
```

### 配置分组

| 组 | 配置项 |
|---|--------|
| LLM | provider, base_url, api_key, model, timeout, max_turns |
| 飞书 | app_id, app_secret, alert_bot_ids, card_signing_key |
| 诊断 | confidence_threshold |
| 安全围栏 | auto_namespaces, max_replica_change, max_auto_fixes, cooldown |
| 监控 | pg/redis/aws enabled |
| 其他 | log_level, embedding |

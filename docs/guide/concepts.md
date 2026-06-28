# 核心概念

了解 ai-fixer 的核心架构和工作原理。

## LangGraph 工作流

ai-fixer 使用 LangGraph 构建了一个 13 节点的状态机，管理从告警接收到问题修复的完整流程。

### 工作流节点

```
ingest → triage → diagnose
  → send_diagnosis_card → await_diagnosis_approval (interrupt)
  → propose → policy_evaluate
  → send_proposal_card → await_proposal_approval (interrupt)
  → execute → verify → resolve/escalate
```

### 节点说明

| 节点 | 功能 |
|------|------|
| `ingest` | 接收和预处理告警消息 |
| `triage` | 告警分类和去重（重复告警直接跳过） |
| `diagnose` | LLM 多轮 agent loop 诊断，调用诊断插件 |
| `send_diagnosis_card` | 发送诊断结果卡片到飞书 |
| `await_diagnosis_approval` | **暂停**，等待用户确认诊断 |
| `propose` | LLM 生成修复方案 |
| `policy_evaluate` | 安全策略评估（风险等级、围栏检查） |
| `send_proposal_card` | 发送修复方案卡片到飞书 |
| `await_proposal_approval` | **暂停**，等待用户确认方案 |
| `execute` | 执行修复操作 |
| `verify` | 验证修复结果 |
| `resolve` | 标记问题已解决 |
| `escalate` | 升级到人工处理 |

### 条件边

工作流包含多个条件分支：

- **重复告警**：`triage` 检测到重复 → 直接 `END`
- **低置信度**：诊断置信度不足 → `escalate`
- **部分失败**：修复执行部分失败 → 回到 `propose`
- **全自动模式**：低风险操作 → 跳过审批直接执行

## 两步人工确认

使用 LangGraph 的 `interrupt/resume` 机制实现：

### 1. 诊断确认

```python
# await_diagnosis_approval 节点
state = interrupt({
    "type": "diagnosis_approval",
    "incident_id": incident_id,
    "diagnosis": diagnosis,
    "confidence": confidence,
    "key_findings": key_findings,
})
```

- LLM 完成诊断后发送卡片
- 卡片显示：诊断结论、置信度、关键发现
- 用户点击「确认诊断」或「拒绝」
- 超过 1 小时未响应自动清理

### 2. 方案确认

```python
# await_proposal_approval 节点
state = interrupt({
    "type": "proposal_approval",
    "incident_id": incident_id,
    "proposal": proposal,
    "risk_level": risk_level,
    "requires_approval": requires_approval,
})
```

- 确认诊断后生成修复方案
- 卡片显示：方案详情、风险等级、预估影响
- 用户确认后执行修复

## 插件系统

### 插件类型

1. **诊断插件（Diagnostic）**
   - 只读操作，用于收集信息
   - LLM 可直接调用，无需审批
   - 示例：`list_pods`, `slow_queries`, `prom.query`

2. **修复插件（Remediation）**
   - 写操作，会修改系统状态
   - 需要经过安全策略评估
   - 示例：`restart_pod`, `scale_deployment`, `kill_deadlock`

### 插件注册

```python
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class MyPlugin(Plugin):
    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="my_plugin",
            description="我的自定义插件",
            category="diagnostic",  # 或 "remediation"
            parameters={...},  # JSON Schema
        )

    async def execute(self, **kwargs) -> dict:
        # 插件逻辑
        return {"result": "..."}
```

### 插件发现

- 内置插件：`app/plugins/builtin/` 目录自动加载
- 自定义插件：`custom_plugins/` 目录自动加载
- 使用 `@register` 装饰器声明式注册

## 执行策略引擎

`ExecutionPolicy` 根据多个因素决定执行方式：

### 风险等级

| 等级 | 说明 | 示例 |
|------|------|------|
| `low` | 低风险，可自动执行 | 查看日志、查询监控 |
| `medium` | 中风险，需要审批 | 重启 Pod、扩缩容 |
| `high` | 高风险，需要审批 | 删除资源、修改配置 |
| `critical` | 极高风险，始终升级 | 删除命名空间、修改 RBAC |

### 决策逻辑

```python
if risk_level == "critical":
    return "escalate"  # 始终升级
elif risk_level in ["low", "medium"]:
    if within_fence(quota_ok):
        return "auto_execute"  # 自动执行
    else:
        return "require_approval"  # 需要审批
else:
    return "require_approval"  # 需要审批
```

### 安全围栏

- **命名空间白名单**：只允许在指定命名空间操作
- **副本数变更限制**：单次变更不超过 50%
- **命令黑名单**：禁止 `rm -rf`、`DROP TABLE` 等危险命令
- **每小时配额**：限制自动修复次数（默认 10 次/小时）

## 数据持久化

### PostgreSQL + pgvector

- **Incident 表**：告警记录和指纹去重
- **IncidentEvent 表**：审计时间线
- **Diagnosis 表**：诊断结果
- **FixProposal 表**：修复方案
- **FixExecution 表**：执行记录
- **KnowledgeEntry 表**：知识库条目

### LangGraph Checkpoint

工作流状态通过 `langgraph-checkpoint-postgres` 持久化：
- 支持进程重启后恢复
- `WorkflowRunManager` 管理 pending 状态的工作流
- 超时自动清理（1 小时）

### 向量记忆

- 使用 pgvector 存储 incident 向量
- 语义搜索相似历史问题
- 辅助诊断决策

## 下一步

- [飞书集成](/guide/feishu) - 配置飞书机器人
- [插件系统](/guide/plugins) - 了解和开发插件
- [架构设计](/development/architecture) - 深入了解架构

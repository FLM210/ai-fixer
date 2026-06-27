# ai-fixer

<img src="favicon.svg" alt="ai-fixer" width="240" />

智能运维修复 Agent。以飞书群聊为交互界面，自动诊断告警、提出修复方案，支持全自动执行（带安全围栏）和历史 incident 学习。

## 功能特性

- 🤖 **智能告警处理**：接收飞书群告警，LLM 自动分类、诊断、生成修复方案
- 🔍 **全栈 SRE 能力**：支持 K8s、数据库、中间件、网络、云服务等全栈排查
- 🛠️ **Shell 执行**：LLM 可调用 shell 命令进行实时问题排查
- 📊 **环境上下文**：用户可配置生产环境信息，LLM 据此做更准确判断
- 💬 **飞书集成**：WebSocket 长连接，告警表情回应，诊断结果卡片
- ✅ **两步人工确认**：诊断结果和修复方案均需用户通过飞书卡片确认后才继续执行
- 🔒 **安全围栏**：自动修复需审批，支持命名空间白名单、配额限制
- 📝 **完整记录**：每轮 LLM 对话、工具调用、执行结果全部持久化
- 🌐 **管理后台**：React 前端，配置管理、Incident 查看、插件管理

## 快速开始

```bash
# 一键启动（含 PG + Redis + 后端 + 前端）
make up

# 或仅启动前后端（复用本机 infra-postgres / infra-redis）
make up-dev

# 查看日志
make logs-dev

# 停止
make down-dev
```

### 手动启动

```bash
make install
cp .env.example .env
docker-compose up -d postgres redis
make migrate
make run
```

访问：
- 后端 API：http://localhost:8080
- 前端管理：http://localhost:5173

## 常用命令

```bash
make install    # 安装依赖
make lint       # 代码检查
make fmt        # 格式化
make type       # 类型检查
make test       # 运行测试
make run        # 启动后端
make migrate    # 数据库迁移
make build-ui   # 构建前端
make dev-ui     # 前端开发服务器
```

## 架构

```
飞书群告警 → 机器人检测 → LLM 分类+诊断 → 📨 诊断确认卡片
                                                ↓ 用户确认
                                        LLM 生成修复方案 → 📨 方案确认卡片
                                                ↓ 用户确认
                                          执行修复 → 发送结果卡片
                ↓
        ┌──────────────────────────────────────────────┐
        │          LangGraph 工作流 (13 节点)            │
        │  ingest → triage → diagnose                   │
        │       → send_diagnosis_card                   │
        │       → await_diagnosis_approval (interrupt)  │
        │       → propose → policy_evaluate              │
        │       → send_proposal_card                    │
        │       → await_proposal_approval (interrupt)   │
        │       → execute → verify → resolve/escalate   │
        └──────────────────────────────────────────────┘
                ↓
        PostgreSQL (checkpoint 持久化 + 结果存储)
```

### 两步人工确认

工作流使用 LangGraph `interrupt/resume` 机制实现两步人工确认:

1. **诊断确认**: 诊断完成后工作流暂停, 发送诊断确认卡片 (含诊断结论、置信度、关键证据), 用户点击"确认诊断"或"拒绝"
2. **方案确认**: 确认诊断后制定修复方案, 再次暂停并发送方案确认卡片 (含方案详情、风险等级), 用户确认后才执行修复

确认过程由 `WorkflowRunManager` 管理, 支持进程重启后通过 PostgreSQL checkpoint 恢复。超过 1 小时未确认的 pending run 会自动清理并发送超时通知。

### 插件系统

- `Plugin` ABC + `PluginSpec`（JSON Schema 自描述）
- `@register(global_registry)` 装饰器声明式注册
- 自动发现 `app/plugins/builtin/` 下的插件

### 内置插件

| 类别 | 插件 |
|------|------|
| K8s | describe_pod, list_pods, restart_pod, scale_deployment, rollback_deployment, cordon_node, delete_evicted_pods, get_events, get_pod_logs, top_pods |
| 数据库 | slow_queries, lock_waits, active_connections, replication_lag, table_bloat, kill_deadlock, vacuum_table, terminate_query |
| 监控 | prom.query, prom.query_range, loki.query, sentry.get_issue |
| Shell | shell.exec（诊断用）, shell.exec_write（修复用，需审批） |
| 其他 | runbook.search, llm.kubectl_action |

## 配置

### 环境变量（.env）

仅需配置基础设施连接：

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
```

### 运行时配置（前端管理）

通过 http://localhost:5173/config 管理：

- LLM 参数（provider, model, api_key, timeout）
- 飞书集成（app_id, app_secret, alert_bot_ids）
- 安全围栏（命名空间白名单、配额、cooldown）
- 监控开关（PostgreSQL, Redis, AWS）
- 向量记忆（embedding 配置）

### 环境上下文

通过 http://localhost:5173/environment 配置生产环境信息，LLM 在诊断时会参考：

- 服务列表及依赖关系
- 基础设施信息（集群、节点、数据库）
- 告警严重程度定义
- 常见问题处理方式

## API

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 系统状态 |
| `/api/config` | GET/PUT | 配置管理 |
| `/api/incidents` | GET | Incident 列表 |
| `/api/incidents/{id}` | GET | Incident 详情（含 LLM 对话） |
| `/api/plugins` | GET | 插件列表 |
| `/api/alert` | POST | 接收告警触发工作流 |
| `/api/environment-context` | GET/PUT | 环境上下文 |
| `/api/events` | GET | SSE 实时事件流 |
| `/healthz` | GET | 健康检查 |
| `/metrics` | GET | Prometheus 指标 |

## 技术栈

- **后端**：Python 3.11, FastAPI, SQLAlchemy 2.0, LangGraph
- **前端**：React 19, Vite 8, TypeScript, Tailwind CSS 4, shadcn/ui
- **数据库**：PostgreSQL 16（pgvector）, Redis 7
- **LLM**：Anthropic Claude / OpenAI GPT（可切换）
- **飞书**：lark-oapi WebSocket 长连接
- **可观测性**：structlog, Prometheus, OpenTelemetry

## License

MIT

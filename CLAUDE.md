# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ai-fixer 是一个运维领域的智能修复 Agent，以飞书群聊为交互界面，监听告警并通过 LLM 进行分类、诊断、提出修复方案，支持全自动执行（带安全围栏）或人工审批。核心是一个 LangGraph 状态机，checkpoint 持久化到 PostgreSQL。支持 Kubernetes、PostgreSQL 等多种基础设施，具备从历史 incident 中学习的能力。

## 常用命令

```bash
make install    # uv sync 安装依赖
make lint       # ruff check app tests
make fmt        # ruff format + check --fix
make type       # mypy app
make test       # pytest（asyncio_mode = "auto"）
make run        # uvicorn app.main:app --port 8080 --reload
make migrate    # alembic upgrade head
make build-ui   # 构建前端（frontend/dist/）
make dev-ui     # 启动前端开发服务器（Vite, port 5173）
```

运行单个测试：
```bash
uv run pytest tests/path/to/test_file.py::test_name -v
```

本地开发启动顺序：
```bash
make install && cp .env.example .env && docker-compose up -d postgres redis && make migrate && make run
```

## 架构

### LangGraph 工作流（10 节点状态机）

```
ingest → triage → diagnose → propose → policy_evaluate → await_approval → execute → verify → resolve/escalate
```

- `GraphState`（`app/graph/state.py`）是贯穿全流程的 TypedDict
- 条件边：重复告警跳过 END，低置信度走 escalate，部分失败回到 propose，全 auto_execute 跳过审批
- checkpoint 通过 `langgraph-checkpoint-postgres` 持久化

### 执行策略引擎（`app/engine/policy.py`）

`ExecutionPolicy` 根据操作风险等级和安全围栏决定执行方式：
- critical 风险 → 始终升级
- low/medium 风险 + 在围栏内 + 配额充足 → 自动执行
- 其他 → 需人工审批
- 安全围栏：命名空间白名单、副本数变更幅度、verb 黑名单、每小时配额

### 插件系统（`app/plugins/`）

- `Plugin` ABC + `PluginSpec`（JSON Schema 自描述）
- `@register(global_registry)` 装饰器声明式注册
- `PluginRegistry` 通过 `pkgutil.iter_modules` 自动发现 `builtin/` 下的插件
- 两类：`diagnostic`（只读，LLM agent loop 调用）和 `remediation`（写操作，需人工审批）
- 新增插件：继承 `Plugin`，实现 `spec` 和 `execute`，用 `@register` 注册

### LLM 层（`app/llm/`）

- `LLMClient` ABC 统一接口，`AnthropicClient` / `OpenAIClient` 两个实现
- `build_llm_client(settings)` 工厂方法，由 `LLM_PROVIDER` 环境变量选择
- `diagnose` 节点内有多轮 agent loop（最多 8 轮），LLM 请求 tool call → 插件并行执行 → 结果回传

### 数据库（SQLAlchemy 2.0 async）

- schema: `fixer`
- 核心模型：`Incident`（指纹去重）、`IncidentEvent`（审计时间线）、`Diagnosis`、`DiagnosticPath`、`FixProposal`、`FixExecution`、`LarkCardBinding`、`RepairOutcome`
- Alembic 管理迁移，迁移文件在 `alembic/versions/`

### 飞书集成（`app/lark/`）

- `LarkClient` 用 `lark-oapi` WebSocket 长连接（无需公网 URL）
- `AlertDetector` 按 sender ID 白名单 + 正则识别告警消息
- `CardRenderer` 用 Jinja2 渲染飞书消息卡片
- `CommandParser` 处理 `/status`、`/diag`、`/run`、`/ignore`、`/escalate`、`/help`、`/plugins` 命令

### Incident 记忆（`app/memory/`）

pgvector 向量存储，用于语义搜索相似历史 incident，辅助诊断决策。

### 可观测性（`app/telemetry/`）

- `structlog` 结构化日志
- Prometheus metrics 暴露在 `/metrics`
- OpenTelemetry tracing（OTLP gRPC 或 console fallback）

### 分布式协调（`app/utils/`）

- `EventDedup`：Redis SET NX + TTL 防重复处理
- `DistributedLock`：确保每个 incident 串行执行

### 前端管理后台（`frontend/`）

React + Vite + TypeScript + shadcn/ui 技术栈，提供仪表盘、Incident 列表、配置管理、插件查看功能。

- `src/api/` — 后端 API 封装（axios）
- `src/hooks/` — 自定义 hooks（SSE 实时事件、配置管理）
- `src/pages/` — 页面组件（Dashboard、Incidents、Config、Plugins）
- `src/components/` — 通用组件（Layout 侧边栏布局）
- 开发模式：`make dev-ui`（Vite port 5173，自动代理 `/api` 到后端 8080）
- 生产模式：`make build-ui` 构建到 `frontend/dist/`，FastAPI 通过 `StaticFiles` 托管

### API 路由（`app/api/`）

| 路径 | 功能 |
|------|------|
| `GET /api/status` | 系统概览状态 |
| `GET /api/config` | 获取所有可配置项（分组） |
| `PUT /api/config` | 批量更新配置 |
| `GET /api/incidents` | Incident 列表（分页、筛选） |
| `GET /api/incidents/{id}` | Incident 详情 |
| `GET /api/plugins` | 插件列表 |
| `GET /api/events` | SSE 实时事件流 |

### 动态配置（`app/config/dynamic.py`）

两层配置架构：环境变量（基础设施凭证，不可改）+ 数据库配置（运行时参数，前端可改）。DB 配置优先级高于环境变量，通过 `system_configs` 表存储，`DynamicConfig` 类管理缓存和热更新。

## 配置

环境变量通过 `.env` 文件配置，Pydantic Settings 加载（`app/config/settings.py`）。关键变量：

| 变量 | 用途 |
|------|------|
| `DATABASE_URL` | PostgreSQL 异步连接串 |
| `LLM_PROVIDER` | `anthropic` 或 `openai` |
| `LLM_API_KEY` | LLM API 密钥 |
| `REDIS_URL` | Redis 连接（锁/去重） |
| `LARK_APP_ID` / `LARK_APP_SECRET` | 飞书机器人凭证 |
| `ALERT_BOT_IDS` | 逗号分隔的告警机器人 sender ID |
| `CARD_SIGNING_KEY` | 卡片按钮 HMAC 签名密钥 |

## 测试

- 测试框架：pytest + pytest-asyncio（`asyncio_mode = "auto"`）
- HTTP mock：`respx`
- K8s mock：`FakeK8sClient`（`app/k8s/client.py`）
- 集成测试：`tests/integration/test_e2e.py`
- CI 会在 PostgreSQL 16 容器上跑完整测试
- 测试中每个用例自动隔离全局插件注册表（`conftest.py` 中的 `_registry_snapshot` fixture）

## 代码风格

- Python 3.11，全部 async/await
- Ruff 规则：E/F/W/I/B/UP/ASYNC/SIM/RUF，行宽 100
- 类型注解严格（mypy strict mode + pydantic plugin），新增代码必须带完整类型标注

## 部署

- Helm chart：`deploy/helm/k8s-fixer/`（Deployment + Service + RBAC + ConfigMap + Secret + MigrateJob + CleanupCronJob + ServiceMonitor）
- Grafana dashboard：`deploy/grafana/k8s-fixer-overview.json`
- 生产 compose：`deploy/docker-compose.prod.yml`
- CI：GitHub Actions（lint → type check → migrate → test with coverage）

# ai-fixer

智能运维修复 Agent — 以飞书群聊为交互界面，自动诊断告警、提出修复方案。

## 功能特性

- 🤖 **智能告警处理**：接收飞书群告警，LLM 自动分类、诊断、生成修复方案
- 🔍 **全栈 SRE 能力**：支持 K8s、数据库、中间件、网络、云服务等全栈排查
- 🛠️ **Shell 执行**：LLM 可调用 shell 命令进行实时问题排查
- 📊 **环境上下文**：用户可配置生产环境信息，LLM 据此做更准确判断
- 💬 **飞书集成**：WebSocket 长连接，告警表情回应，诊断结果卡片
- ✅ **两步人工确认**：诊断结果和修复方案均需用户通过飞书卡片确认后才继续执行
- 🔒 **安全围栏**：自动修复需审批，支持命名空间白名单、配额限制
- 📝 **完整记录**：每轮 LLM 对话、工具调用、执行结果全部持久化
- 📚 **知识库**：运维知识条目管理，向量检索辅助诊断
- 🌐 **管理后台**：React 前端，配置管理、Incident 查看、插件管理、知识库管理
- 🔌 **插件热更新**：支持在线启用/禁用、上传自定义插件

## 快速开始

```bash
# 克隆项目
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer

# 一键启动（含 PG + Redis + 后端 + 前端）
make up

# 或仅启动前后端（复用本机数据库）
make up-dev
```

访问：
- 前端管理：http://localhost:5173
- 后端 API：http://localhost:8080
- 健康检查：http://localhost:8080/healthz

## 文档导航

| 章节 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 安装、配置、首次运行 |
| [配置指南](configuration.md) | 环境变量、运行时配置、环境上下文 |
| [插件系统](plugins.md) | 内置插件、自定义插件、热更新 |
| [前端管理](frontend.md) | Dashboard、Incidents、配置管理 |
| [API 参考](api.md) | REST API 端点文档 |
| [架构设计](architecture.md) | 系统架构、工作流、数据模型 |
| [部署指南](deployment.md) | Docker、Kubernetes、生产环境 |

## 技术栈

- **后端**：Python 3.11, FastAPI, SQLAlchemy 2.0, LangGraph
- **前端**：React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui
- **数据库**：PostgreSQL 16, Redis 7
- **LLM**：Anthropic Claude / OpenAI GPT（可切换）
- **飞书**：lark-oapi WebSocket 长连接

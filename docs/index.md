---
layout: home

hero:
  name: ai-fixer
  text: 智能运维修复 Agent
  tagline: 以飞书群聊为交互界面，自动诊断告警、提出修复方案，支持全自动执行和历史 incident 学习
  image:
    src: /favicon.svg
    alt: ai-fixer
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 部署指南
      link: /deployment/
    - theme: alt
      text: GitHub
      link: https://github.com/FLM210/ai-fixer

features:
  - icon: 🤖
    title: 智能告警处理
    details: 接收飞书群告警，LLM 自动分类、诊断、生成修复方案
  - icon: 🔍
    title: 全栈 SRE 能力
    details: 支持 K8s、数据库、中间件、网络、云服务等全栈排查
  - icon: ✅
    title: 两步人工确认
    details: 诊断结果和修复方案均需用户通过飞书卡片确认后才继续执行
  - icon: 🛠️
    title: Shell 执行
    details: LLM 可调用 shell 命令进行实时问题排查
  - icon: 🔒
    title: 安全围栏
    details: 自动修复需审批，支持命名空间白名单、配额限制
  - icon: 📊
    title: 环境上下文
    details: 用户可配置生产环境信息，LLM 据此做更准确判断
  - icon: 💬
    title: 飞书集成
    details: WebSocket 长连接，告警表情回应，诊断结果卡片
  - icon: 📝
    title: 完整记录
    details: 每轮 LLM 对话、工具调用、执行结果全部持久化
  - icon: 🌐
    title: 管理后台
    details: React 前端，配置管理、Incident 查看、插件管理
---

## 快速体验

```bash
# 克隆项目
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer

# 一键启动
make up

# 访问管理后台
open http://localhost:5173
```

## 工作原理

ai-fixer 的核心是一个基于 LangGraph 的状态机工作流，将告警处理抽象为严谨的步骤，确保每一步诊断和修复都在可控和安全的前提下进行：

```mermaid
graph TD
    Alert[飞书群告警] --> Bot[机器人检测]
    Bot --> Triage[LLM 分类与初步分析]
    Triage --> Diagnose[诊断问题并获取上下文]
    
    Diagnose --> Card1[发送诊断确认卡片]
    Card1 -->|用户点击确认| Propose[生成修复方案]
    
    Propose --> Evaluate[策略与围栏评估]
    Evaluate --> Card2[发送方案确认卡片]
    
    Card2 -->|用户点击确认| Execute[执行修复步骤]
    Execute --> Verify[验证修复结果]
    Verify --> Notify[发送最终结果卡片]
    
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef highlight fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef warning fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    
    class Card1,Card2 warning;
    class Triage,Diagnose,Propose highlight;
```

## 技术栈

- **后端**：Python 3.11, FastAPI, SQLAlchemy 2.0, LangGraph
- **前端**：React 19, Vite 8, TypeScript, Tailwind CSS 4, shadcn/ui
- **数据库**：PostgreSQL 16（pgvector）, Redis 7
- **LLM**：Anthropic Claude / OpenAI GPT（可切换）
- **飞书**：lark-oapi WebSocket 长连接
- **可观测性**：structlog, Prometheus, OpenTelemetry

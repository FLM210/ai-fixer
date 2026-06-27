# AGENTS.md

This file provides guidance to AI agents (Claude Code, Codex, etc.) when working with code in this repository.

**完整文档请参阅 [CLAUDE.md](CLAUDE.md)**，本文件仅列出通用要点。

## 项目概述

ai-fixer 是一个运维领域的智能修复 Agent，以飞书群聊为交互界面，监听告警并通过 LLM 进行分类、诊断、提出修复方案。核心是一个 13 节点 LangGraph 状态机，支持两步人工确认（诊断确认 + 方案确认）。

## 常用命令

```bash
make install    # 安装依赖
make lint       # 代码检查
make run        # 启动后端 (localhost:8080)
make test       # 运行测试
make migrate    # 数据库迁移
make build-ui   # 构建前端
```

## 关键约束

- Python 3.11，全部 async/await
- Ruff 规则行宽 100，mypy strict mode
- `DATABASE_URL` 和 `REDIS_URL` 是启动必需的环境变量
- 飞书集成需要 `LARK_APP_ID` 和 `LARK_APP_SECRET`
- 前端 `base: '/app/'`，生产环境通过 `SERVE_STATIC=1` 托管

## 架构速览

```
告警 → ingest → triage → diagnose
          → send_diagnosis_card → await_diagnosis_approval (interrupt)
          → propose → policy_evaluate
          → send_proposal_card → await_proposal_approval (interrupt)
          → execute → verify → resolve/escalate
```

详细架构说明、API 路由、插件系统、配置系统等请参阅 [CLAUDE.md](CLAUDE.md)。

# ai-fixer 文档

本目录包含 ai-fixer 项目的完整文档，使用 VitePress 构建。

## 本地开发

### 安装依赖

```bash
cd docs
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173 预览文档。

### 构建静态文件

```bash
npm run build
```

生成的文件在 `.vitepress/dist/` 目录。

## 文档结构

```
docs/
├── .vitepress/
│   └── config.mts        # VitePress 配置
├── index.md              # 首页
├── guide/                # 使用指南
│   ├── index.md          # 什么是 ai-fixer
│   ├── quick-start.md    # 快速开始
│   ├── concepts.md       # 核心概念
│   ├── feishu.md         # 飞书集成
│   ├── alerts.md         # 告警处理
│   ├── plugins.md        # 插件系统
│   ├── dashboard.md      # 管理后台
│   ├── configuration.md  # 配置管理
│   └── environment.md    # 环境上下文
├── deployment/           # 部署文档
│   ├── index.md          # 部署概览
│   ├── feishu-bot.md     # 飞书机器人创建
│   ├── infrastructure.md # 基础设施准备
│   ├── docker.md         # Docker 部署
│   ├── kubernetes.md     # Kubernetes 部署
│   ├── production.md     # 生产环境加固
│   └── troubleshooting.md # 故障排查
├── development/          # 开发文档
│   ├── index.md          # 开发指南
│   ├── architecture.md   # 架构设计
│   ├── plugin-dev.md     # 插件开发
│   ├── testing.md        # 测试
│   └── contributing.md   # 贡献指南
├── api/                  # API 文档
│   ├── index.md          # API 概览
│   ├── rest.md           # REST API
│   └── webhook.md        # Webhook
└── public/               # 静态资源
    └── favicon.svg       # Logo
```

## 添加新文档

1. 在对应目录下创建 `.md` 文件
2. 更新 `docs/.vitepress/config.mts` 中的侧边栏配置
3. 提交更改，GitHub Actions 会自动部署

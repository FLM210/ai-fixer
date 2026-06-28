# 快速开始

本文档帮助你在 5 分钟内启动 ai-fixer 并进行基本测试。

## 前提条件

- Python 3.11+
- Docker
- Git
- PostgreSQL 14+（已部署）
- Redis 6.0+（已部署）

## 配置环境变量

```bash
# 克隆项目
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer

# 创建环境变量文件
cp .env.example .env
```

编辑 `.env` 文件，配置数据库和 Redis 连接：

```bash
# 基础设施连接（必需）
DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
REDIS_URL=redis://your-redis-host:6379/0
```

## 启动应用

### 方式 1：Docker（推荐）

```bash
# 构建并启动
make up

# 或直接使用 Docker
docker run -d \
  --name ai-fixer \
  -p 8080:8080 \
  --env-file .env \
  hahtangtang/ai-fixer:latest
```

### 方式 2：本地运行

```bash
# 安装依赖
make install

# 执行数据库迁移
make migrate

# 启动后端
make run

# 启动前端（可选，另一个终端）
make dev-ui
```

## 访问服务

- 后端 API：http://localhost:8080
- 前端管理：http://localhost:8080
- API 文档：http://localhost:8080/docs

## 配置 LLM

启动后需要在前端配置 LLM：

1. 访问 http://localhost:8080
2. 在「LLM 配置」区域填写：
   - **Provider**: `anthropic` 或 `openai`
   - **API Key**: 你的 API 密钥
   - **Model**: 如 `claude-3-5-sonnet-20241022`
3. 点击保存

## 配置飞书集成

详见 [飞书集成](/guide/feishu) 文档。

## 测试告警处理

### 方式 1：通过 API 触发

```bash
curl -X POST http://localhost:8080/api/alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": "[告警] Pod CrashLoopBackOff\n服务: user-service\n命名空间: production\nPod: user-service-abc123",
    "sender_id": "test_bot"
  }'
```

### 方式 2：通过飞书群触发

1. 将机器人添加到告警群组
2. 在群组中 @机器人 并发送告警消息
3. 观察诊断卡片和修复方案

## 查看结果

1. **飞书群**：会收到诊断卡片和修复方案卡片
2. **管理后台**：http://localhost:8080 查看 Incident 详情
3. **日志**：`make logs-dev` 查看实时日志

## 常用命令

```bash
make up          # 一键启动所有服务
make down        # 停止所有服务
make logs        # 查看日志
make logs-dev    # 查看开发模式日志
make migrate     # 执行数据库迁移
make test        # 运行测试
make lint        # 代码检查
make fmt         # 代码格式化
```

## 下一步

- [核心概念](/guide/concepts) - 了解工作流和插件系统
- [飞书集成](/guide/feishu) - 完整配置飞书机器人
- [部署指南](/deployment/) - 生产环境部署

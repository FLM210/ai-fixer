# 快速开始

## 环境要求

- Python 3.11+
- Docker & Docker Compose
- Node.js 20+（前端开发）

## 安装

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目
git clone https://github.com/your-org/ai-fixer.git
cd ai-fixer

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库连接信息

# 一键启动
make up
```

### 方式二：手动安装

```bash
# 安装 Python 依赖
make install

# 启动数据库
docker-compose up -d postgres redis

# 配置环境变量
cp .env.example .env

# 执行数据库迁移
make migrate

# 启动后端
make run

# 另开终端，启动前端
make dev-ui
```

## 环境变量配置

最小化 `.env` 配置：

```env
# 数据库（必填）
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

其他配置（LLM、飞书、安全围栏等）通过前端管理页面配置，无需写入 `.env`。

完整环境变量说明见 [配置指南](configuration.md)。

## 首次访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端管理 | http://localhost:5173 | React 管理后台 |
| 后端 API | http://localhost:8080 | FastAPI 服务 |
| 健康检查 | http://localhost:8080/healthz | 服务状态 |
| Prometheus | http://localhost:8080/metrics | 监控指标 |

## 验证安装

```bash
# 检查后端健康状态
curl http://localhost:8080/healthz

# 检查插件加载
curl http://localhost:8080/api/plugins | python3 -m json.tool

# 发送测试告警
curl -X POST http://localhost:8080/api/alert \
  -H 'Content-Type: application/json' \
  -d '{"text":"🔴 Firing\n告警名称: Test\n严重程度: P2\n服务: test\n详情: 测试告警","source":"test"}'
```

## 下一步

- [配置飞书机器人](configuration.md#飞书集成)
- [配置 LLM](configuration.md#llm-配置)
- [添加环境上下文](configuration.md#环境上下文)
- [管理插件](plugins.md)

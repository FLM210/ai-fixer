# 基础设施准备

部署 ai-fixer 所需的外部基础设施。

> **重要**：ai-fixer 只负责应用本身，PostgreSQL 和 Redis 作为独立的基础设施服务，请提前准备好。

## 系统要求

| 组件 | 版本要求 | 用途 | 部署方式 |
|------|---------|------|---------|
| PostgreSQL | 14+ | 数据存储 | 外部服务 |
| Redis | 6.0+ | 分布式锁、去重、缓存 | 外部服务 |
| Python | 3.11+ | 运行环境 | 容器内 |

## PostgreSQL 要求

### 必需扩展

PostgreSQL 需要安装以下扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector 向量存储
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 全文搜索优化
```

### 连接信息

准备好以下连接信息：

```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

示例：

```
DATABASE_URL=postgresql+asyncpg://fixer:your_password@192.168.1.100:5432/fixer
```

### 权限要求

数据库用户需要以下权限：

- CREATE TABLE
- CREATE INDEX
- CREATE EXTENSION
- INSERT, UPDATE, DELETE, SELECT

```sql
-- 创建数据库和用户
CREATE USER fixer WITH PASSWORD 'your_password';
CREATE DATABASE fixer OWNER fixer;
GRANT ALL PRIVILEGES ON DATABASE fixer TO fixer;
```

## Redis 要求

### 连接信息

准备好以下连接信息：

```
REDIS_URL=redis://host:port/database
```

示例：

```
REDIS_URL=redis://192.168.1.100:6379/0
```

如果 Redis 有密码：

```
REDIS_URL=redis://:your_password@192.168.1.100:6379/0
```

### 权限要求

Redis 需要支持以下操作：

- SET / GET
- SETEX
- DEL
- PING

## LLM API 准备

### Anthropic

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 创建 API Key
3. 记录配置：

```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxxxxx
LLM_MODEL=claude-3-5-sonnet-20241022
```

### OpenAI

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 创建 API Key
3. 记录配置：

```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=gpt-4o
```

### 自定义 LLM

如果使用其他 LLM 服务（兼容 OpenAI 接口）：

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://your-llm-endpoint.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```

## 网络要求

### 入站流量

| 端口 | 协议 | 用途 |
|------|------|------|
| 8080 | HTTP | API 服务和前端管理 |

### 出站流量

| 目标 | 端口 | 用途 |
|------|------|------|
| PostgreSQL | 5432 | 数据库连接 |
| Redis | 6379 | 缓存连接 |
| open.feishu.cn | 443 | 飞书 API |
| api.anthropic.com | 443 | Anthropic LLM |
| api.openai.com | 443 | OpenAI LLM |

## 验证清单

- [ ] PostgreSQL 可连接，pgvector 扩展已安装
- [ ] Redis 可连接
- [ ] LLM API Key 有效
- [ ] 飞书应用已创建
- [ ] 飞书权限已配置
- [ ] 网络访问正常

## 下一步

- [Docker 部署](/deployment/docker) - Docker 部署应用
- [Kubernetes 部署](/deployment/kubernetes) - K8s 部署
- [飞书机器人创建](/deployment/feishu-bot) - 配置飞书集成

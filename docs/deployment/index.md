# 部署概览

ai-fixer 只负责应用本身，PostgreSQL 和 Redis 作为独立的基础设施服务。

## 部署方式

### Docker（推荐）

最简单的部署方式。

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和 Redis 连接

# 启动应用
docker run -d \
  --name ai-fixer \
  -p 8080:8080 \
  --env-file .env \
  hahtangtang/ai-fixer:latest
```

**文档**：[Docker 部署](/deployment/docker)

### Kubernetes（推荐生产环境）

适合生产环境，支持高可用和自动扩缩容。

```bash
# 创建 Secret
kubectl create secret generic ai-fixer-secrets \
  --from-literal=database-url='postgresql+asyncpg://...' \
  --from-literal=redis-url='redis://...' \
  -n ai-fixer

# 使用 Helm Chart 部署
cd deploy/helm/k8s-fixer
helm install ai-fixer . -n ai-fixer -f values.yaml
```

**文档**：[Kubernetes 部署](/deployment/kubernetes)

### 直接运行

适合开发调试。

```bash
make install
cp .env.example .env
# 编辑 .env 配置数据库和 Redis 连接
make migrate
make run
```

**文档**：[开发指南](/development/)

## 系统要求

### 硬件要求（应用）

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB |

### 软件要求

| 组件 | 版本要求 | 说明 | 部署方式 |
|------|---------|------|---------|
| Python | 3.11+ | 运行环境 | 容器内 |
| PostgreSQL | 14+ | 需要 pgvector 扩展 | 外部服务 |
| Redis | 6.0+ | 分布式锁和去重 | 外部服务 |
| Docker | 20.10+ | 容器化部署 | - |
| Kubernetes | 1.24+ | K8s 部署（可选） | - |

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

## 部署流程

### 1. 准备阶段

- [ ] 准备 PostgreSQL 数据库（含 pgvector 扩展）
- [ ] 准备 Redis 实例
- [ ] 创建飞书应用和机器人
- [ ] 获取 LLM API 密钥

### 2. 部署阶段

- [ ] 配置环境变量（数据库、Redis 连接）
- [ ] 启动应用服务
- [ ] 执行数据库迁移
- [ ] 配置飞书事件订阅

### 3. 验证阶段

- [ ] 检查服务健康状态
- [ ] 测试飞书机器人响应
- [ ] 测试告警处理流程
- [ ] 检查日志和监控

## 配置管理

### 环境变量

基础配置通过环境变量管理：

```bash
# 必需配置
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
```

### 运行时配置

业务配置通过前端管理后台动态管理：

- LLM 参数（provider, model, api_key）
- 飞书集成（app_id, app_secret, alert_bot_ids）
- 安全围栏（命名空间白名单、配额）
- 监控开关

详见 [配置管理](/guide/configuration)

## 监控和日志

### Prometheus 指标

应用暴露 Prometheus 指标在 `/metrics` 端点：

```bash
curl http://localhost:8080/metrics
```

### Grafana Dashboard

提供预置的 Grafana Dashboard：

```bash
# 导入 Dashboard
deploy/grafana/k8s-fixer-overview.json
```

### 日志

使用 structlog 结构化日志：

```bash
# Docker
docker logs -f ai-fixer

# Kubernetes
kubectl logs -f deployment/ai-fixer -n ai-fixer
```

## 下一步

根据你的环境选择部署方式：

- [飞书机器人创建](/deployment/feishu-bot) - 创建飞书应用
- [基础设施准备](/deployment/infrastructure) - 准备数据库和 Redis
- [Docker 部署](/deployment/docker) - Docker 部署
- [Kubernetes 部署](/deployment/kubernetes) - K8s 部署
- [生产环境加固](/deployment/production) - 安全和监控配置

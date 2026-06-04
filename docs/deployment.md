# 部署指南

## Docker Compose 部署

### 全量部署（含数据库）

```bash
# 克隆项目
git clone https://github.com/your-org/ai-fixer.git
cd ai-fixer

# 配置环境变量
cp .env.example .env

# 一键启动
make up

# 查看日志
make logs

# 停止
make down
```

### 仅部署应用（复用已有数据库）

```bash
# 确保 PostgreSQL 和 Redis 已运行
# 修改 .env 中的连接信息

make up-dev

# 查看日志
make logs-dev

# 停止
make down-dev
```

### Docker Compose 文件说明

**docker-compose.yml**（全量）

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | PostgreSQL 16 |
| redis | 6379 | Redis 7 |
| backend | 8080 | 后端 API |
| frontend | 5173 | 前端开发服务器 |

**docker-compose.dev.yml**（仅应用）

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8080 | 后端 API |
| frontend | 5173 | 前端开发服务器 |

通过 `host.docker.internal` 连接本机数据库。

## Kubernetes 部署

### Helm Chart

```bash
# 添加 Helm 仓库（如果有）
helm repo add ai-fixer https://your-org.github.io/ai-fixer

# 安装
helm install ai-fixer deploy/helm/k8s-fixer \
  --namespace ai-fixer \
  --create-namespace \
  --set databaseUrl=postgresql+asyncpg://user:pass@pg:5432/db \
  --set redisUrl=redis://redis:6379/0
```

### Helm Chart 组件

| 组件 | 说明 |
|------|------|
| Deployment | 后端服务 |
| Service | ClusterIP 服务 |
| RBAC | ServiceAccount + Role/RoleBinding |
| ConfigMap | 非敏感配置 |
| Secret | 敏感配置 |
| MigrateJob | 数据库迁移 Job |
| CleanupCronJob | 每日清理（保留 180 天） |
| ServiceMonitor | Prometheus 监控 |

### 生产环境配置

```yaml
# values-prod.yaml
replicaCount: 2

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

databaseUrl: postgresql+asyncpg://user:pass@pg:5432/db
redisUrl: redis://redis:6379/0

ingress:
  enabled: true
  host: fixer.example.com
```

## 生产环境建议

### 数据库

- 使用 PostgreSQL 14+
- 启用 pgvector 扩展（用于向量记忆）
- 配置定期备份
- 建议使用 RDS 或 Cloud SQL

### Redis

- 用于分布式锁和事件去重
- 建议使用 ElastiCache 或 Cloud Memorystore
- 单节点即可，不需要集群

### LLM

- 推荐使用 Anthropic Claude（claude-sonnet-4-6）
- 配置 API Key 通过前端管理页面
- 监控 token 使用量

### 飞书

1. 创建飞书应用
2. 开启 WebSocket 长连接
3. 配置事件订阅：`im.message.receive_v1`
4. 配置权限：`im:message`
5. 将机器人加入告警群

### 监控

- Prometheus 指标：`/metrics`
- Grafana Dashboard：`deploy/grafana/k8s-fixer-overview.json`
- 日志：structlog JSON 格式

### 安全

- 使用 Secret 管理敏感配置
- 限制 RBAC 权限
- 启用安全围栏
- 定期审查插件

## 环境变量参考

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | ✅ | PostgreSQL 连接串 |
| `REDIS_URL` | ✅ | Redis 连接串 |
| `HTTP_HOST` | | 监听地址（默认 0.0.0.0） |
| `HTTP_PORT` | | 监听端口（默认 8080） |
| `LOG_LEVEL` | | 日志级别（默认 INFO） |
| `CUSTOM_PLUGINS_DIR` | | 自定义插件目录（默认 ./custom_plugins） |
| `SERVE_STATIC` | | 设为 1 启用静态文件托管 |

## 升级

```bash
# 拉取最新代码
git pull

# 重新构建
make up-dev --build

# 执行数据库迁移（自动）
# 容器启动时自动执行 alembic upgrade head
```

## 故障排查

### 后端无法启动

```bash
# 查看日志
make logs-dev

# 检查数据库连接
docker exec infra-postgres psql -U app_user -d app_db -c "SELECT 1"

# 检查 Redis
docker exec infra-redis redis-cli ping
```

### LLM 无响应

1. 检查 LLM 配置：http://localhost:5173/config
2. 验证 API Key 有效性
3. 查看后端日志中的 LLM 错误

### 飞书不触发

1. 检查飞书配置：app_id、app_secret
2. 确认事件订阅已配置：`im.message.receive_v1`
3. 确认机器人已加入群聊
4. 查看后端日志中的飞书连接状态

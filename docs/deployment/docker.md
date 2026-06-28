# Docker 部署

使用 Docker 部署 ai-fixer 应用。

> **注意**：ai-fixer 需要 PostgreSQL 和 Redis 作为基础设施，请提前准备好。

## 快速启动

### 1. 克隆项目

```bash
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接：

```bash
DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
REDIS_URL=redis://your-redis-host:6379/0
```

### 3. 启动应用

```bash
docker run -d \
  --name ai-fixer \
  -p 8080:8080 \
  -e DATABASE_URL="postgresql+asyncpg://user:password@your-postgres-host:5432/fixer" \
  -e REDIS_URL="redis://your-redis-host:6379/0" \
  hahtangtang/ai-fixer:latest
```

### 4. 访问服务

- 后端 API：http://localhost:8080
- 前端管理：http://localhost:8080
- API 文档：http://localhost:8080/docs

## 详细配置

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    image: hahtangtang/ai-fixer:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
      - REDIS_URL=redis://your-redis-host:6379/0
    env_file:
      - .env
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 环境变量

在 `.env` 文件中配置：

```bash
# 基础设施连接（必需）
DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
REDIS_URL=redis://your-redis-host:6379/0

# 飞书配置（部署后通过前端配置）
# LARK_APP_ID=cli_xxxxxxxx
# LARK_APP_SECRET=xxxxxxxx

# LLM 配置（部署后通过前端配置）
# LLM_PROVIDER=anthropic
# LLM_API_KEY=sk-xxxxxxxx
```

## 常用命令

### 服务管理

```bash
# 启动应用
docker run -d --name ai-fixer -p 8080:8080 --env-file .env hahtangtang/ai-fixer:latest

# 停止应用
docker stop ai-fixer

# 重启应用
docker restart ai-fixer

# 查看容器状态
docker ps

# 查看日志
docker logs -f ai-fixer

# 查看实时日志
docker logs --tail 100 -f ai-fixer
```

### 开发命令

```bash
# 安装依赖
make install

# 代码检查
make lint

# 代码格式化
make fmt

# 类型检查
make type

# 运行测试
make test
```

## 自定义配置

### 使用 docker-compose.yml

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  app:
    image: hahtangtang/ai-fixer:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
      - REDIS_URL=redis://your-redis-host:6379/0
    env_file:
      - .env
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

启动命令：

```bash
docker-compose up -d
```

### 自定义端口

修改端口映射：

```yaml
services:
  app:
    ports:
      - "9000:8080"  # 将 8080 映射到 9000
```

## 故障排查

### 服务启动失败

```bash
# 查看详细日志
docker logs ai-fixer

# 检查容器状态
docker ps -a

# 检查资源使用
docker stats ai-fixer
```

### 数据库连接失败

```bash
# 检查 DATABASE_URL 配置
docker exec ai-fixer env | grep DATABASE_URL

# 测试数据库连接
docker exec ai-fixer python -c "import asyncpg; print('asyncpg ok')"
```

### Redis 连接失败

```bash
# 检查 REDIS_URL 配置
docker exec ai-fixer env | grep REDIS_URL

# 测试 Redis 连接
docker exec ai-fixer python -c "import redis; print('redis ok')"
```

### 端口冲突

```bash
# 检查端口占用
lsof -i :8080

# 修改端口映射
# 编辑 docker-compose.yml 或 docker run 命令
```

## 生产环境建议

### 安全加固

1. **使用强密码**：
   ```bash
   openssl rand -hex 32  # 生成数据库密码
   ```

2. **限制网络访问**：
   - 使用防火墙限制访问
   - 不暴露不必要的端口

3. **启用 HTTPS**：使用 Nginx 或 Traefik 反向代理

### 监控配置

1. 启用 Prometheus 指标
2. 导入 Grafana Dashboard
3. 配置告警通知

详见 [生产环境加固](/deployment/production)

## 下一步

- [飞书机器人创建](/deployment/feishu-bot) - 配置飞书集成
- [生产环境加固](/deployment/production) - 安全和监控配置
- [开发指南](/development/) - 本地开发配置

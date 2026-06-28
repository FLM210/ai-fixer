# ai-fixer 完整部署指南

本文档提供从零开始部署 ai-fixer 的完整流程，包括飞书机器人创建和应用部署。

> **重要**：ai-fixer 只负责应用本身，PostgreSQL 和 Redis 作为独立的基础设施服务，请提前准备好。

## 目录

1. [飞书机器人创建](#1-飞书机器人创建)
2. [基础设施准备](#2-基础设施准备)
3. [应用部署](#3-应用部署)
4. [飞书机器人配置](#4-飞书机器人配置)
5. [验证部署](#5-验证部署)

---

## 1. 飞书机器人创建

### 1.1 创建应用

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 点击「创建企业自建应用」
3. 填写应用信息：
   - **应用名称**: `ai-fixer`（或自定义名称）
   - **应用描述**: 智能运维修复助手
   - **应用图标**: 上传合适的图标

### 1.2 启用机器人能力

1. 进入应用详情页 → 「应用能力」→「机器人」
2. 点击「启用机器人」
3. 记录 `App ID` 和 `App Secret`（后续配置需要）

### 1.3 配置权限

进入「权限管理」页面，申请以下权限：

#### 消息相关权限（必需）
| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取与发送单聊消息 | `im:message` | 接收和发送消息 |
| 获取群组消息 | `im:message.group_at_msg` | 接收群组 @消息 |
| 获取用户发给机器人的单聊消息 | `im:message.p2p_msg` | 接收单聊消息 |
| 读取消息内容 | `im:message:readonly` | 读取消息详情 |
| 发送消息 | `im:message:send_as_bot` | 发送消息 |

#### 卡片相关权限（必需）
| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 创建交互卡片 | `im:message.interactive` | 发送交互卡片 |

#### 群组相关权限（可选）
| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取群组信息 | `im:chat:readonly` | 获取群组详情 |

### 1.4 获取加密配置

1. 进入「事件订阅」页面
2. 记录以下信息：
   - **Verification Token**: 用于验证请求来源
   - **Encrypt Key**: 用于解密事件数据（AES-256-CBC）

### 1.5 配置事件订阅（暂时跳过，部署后配置）

> 注意：需要先完成应用部署获取公网地址后再回来配置

---

## 2. 基础设施准备

### 2.1 系统要求

| 组件 | 版本要求 | 说明 | 部署方式 |
|------|---------|------|---------|
| Python | 3.11+ | 运行环境 | 容器内 |
| PostgreSQL | 14+ | 需要 pgvector 扩展 | 外部服务 |
| Redis | 6.0+ | 分布式锁和去重 | 外部服务 |

### 2.2 PostgreSQL 要求

#### 必需扩展

PostgreSQL 需要安装以下扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector 向量存储
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 全文搜索优化
```

#### 权限要求

数据库用户需要以下权限：

```sql
-- 创建数据库和用户
CREATE USER fixer WITH PASSWORD 'your_secure_password';
CREATE DATABASE fixer OWNER fixer;
GRANT ALL PRIVILEGES ON DATABASE fixer TO fixer;
```

#### 记录连接信息

```bash
DATABASE_URL=postgresql+asyncpg://fixer:your_secure_password@your-postgres-host:5432/fixer
```

### 2.3 Redis 要求

Redis 版本 >= 6.0，支持以下操作：SET、GET、SETEX、DEL、PING

#### 记录连接信息

```bash
REDIS_URL=redis://your-redis-host:6379/0
# 如果有密码
REDIS_URL=redis://:your_password@your-redis-host:6379/0
```

---

## 3. 应用部署

### 3.1 方式 A: Docker 部署（推荐）

#### 启动应用

```bash
# 创建环境变量文件
cp .env.example .env

# 编辑 .env 文件，填入数据库和 Redis 连接信息
vim .env

# 启动应用
docker run -d \
  --name ai-fixer \
  -p 8080:8080 \
  --env-file .env \
  hahtangtang/ai-fixer:latest

# 执行数据库迁移
docker exec ai-fixer alembic upgrade head

# 查看日志
docker logs -f ai-fixer
```

#### 使用 docker-compose.yml

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  app:
    image: hahtangtang/ai-fixer:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql+asyncpg://fixer:your_secure_password@your-postgres-host:5432/fixer
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

### 3.2 方式 B: Helm Chart 部署（推荐生产环境）

#### 创建 Secret

```bash
kubectl create secret generic ai-fixer-secrets \
  --from-literal=database-url='postgresql+asyncpg://fixer:your_secure_password@your-postgres-host:5432/fixer' \
  --from-literal=redis-url='redis://your-redis-host:6379/0' \
  --from-literal=llm-api-key='sk-xxxxxxxx' \
  -n ai-fixer
```

#### 准备 values.yaml

```yaml
# values.yaml
image:
  repository: hahtangtang/ai-fixer
  tag: latest

replicaCount: 1

service:
  type: ClusterIP
  port: 8080

env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: database-url
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: redis-url
  - name: LLM_API_KEY
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: llm-api-key

config:
  LLM_PROVIDER: "anthropic"
  LOG_LEVEL: "info"

# 不需要创建 Secret（已手动创建）
secrets:
  create: false
```

#### 部署命令

```bash
# 创建命名空间
kubectl create namespace ai-fixer

# 部署
cd deploy/helm/k8s-fixer
helm install ai-fixer . -n ai-fixer -f values.yaml

# 查看状态
kubectl get pods -n ai-fixer
kubectl logs -f deployment/ai-fixer -n ai-fixer
```

### 3.3 方式 C: 直接运行（开发调试）

```bash
# 克隆代码
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer

# 安装依赖
make install

# 配置环境变量
cp .env.example .env
vim .env

# 执行数据库迁移
make migrate

# 构建前端（可选）
make build-ui

# 启动服务
SERVE_STATIC=1 make run
```

---

## 4. 飞书机器人配置

### 4.1 配置环境变量

在 `.env` 文件中添加：

```bash
# 飞书应用凭证
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 事件加密配置
LARK_ENCRYPT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LARK_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 告警机器人 ID（逗号分隔）
ALERT_BOT_IDS=cli_xxxxxxxx,cli_yyyyyyyy
```

### 4.2 获取告警机器人 ID

1. 在飞书开放平台 → 「应用管理」中找到告警机器人应用
2. 进入应用详情 → 「凭证与基础信息」
3. 记录 `App ID` 作为 `ALERT_BOT_IDS`

### 4.3 配置事件订阅

1. 返回飞书开放平台 → ai-fixer 应用
2. 进入「事件订阅」页面
3. 配置请求地址：`https://your-domain.com/lark/event`
4. 添加事件：
   - `im.message.receive_v1` - 接收消息
   - `im.message.reaction.created_v1` - 消息表情回复（可选）

### 4.4 添加机器人到群组

1. 在飞书中创建或进入告警群组
2. 点击群设置 → 「群机器人」→「添加机器人」
3. 搜索并添加 `ai-fixer` 机器人
4. 记录机器人的 `open_id`（格式：`ou_xxxxxxxx`）

---

## 5. 验证部署

### 5.1 检查服务状态

```bash
# Docker 环境
docker ps
curl http://localhost:8080/healthz

# Kubernetes 环境
kubectl get pods -n ai-fixer
kubectl port-forward svc/ai-fixer 8080:8080 -n ai-fixer
curl http://localhost:8080/healthz
```

### 5.2 检查数据库迁移

```bash
# Docker 环境
docker exec ai-fixer alembic current

# Kubernetes 环境
kubectl exec -it deployment/ai-fixer -n ai-fixer -- alembic current
```

### 5.3 测试飞书连接

1. 在飞书群组中发送消息：
   ```
   @ai-fixer /help
   ```

2. 期望响应：
   ```
   可用命令：
   /status - 查看系统状态
   /plugins - 查看可用插件
   /diag - 手动触发诊断
   /help - 显示帮助信息
   ```

### 5.4 测试告警处理

1. 发送一条模拟告警消息：
   ```
   @ai-fixer [告警] 测试告警 - Pod Restart
   命名空间: default
   Pod: test-pod-abc123
   状态: CrashLoopBackOff
   ```

2. 期望行为：
   - 收到诊断确认卡片
   - 点击「确认」后收到修复方案卡片
   - 点击「执行」后收到执行结果

---

## 附录 A: 环境变量参考

| 变量名 | 必需 | 说明 | 示例值 |
|-------|------|------|--------|
| `DATABASE_URL` | ✅ | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | Redis 连接串 | `redis://localhost:6379/0` |
| `LARK_APP_ID` | ✅ | 飞书应用 App ID | `cli_xxxxxxxx` |
| `LARK_APP_SECRET` | ✅ | 飞书应用 App Secret | `xxxxxxxx` |
| `LARK_ENCRYPT_KEY` | ✅ | 飞书事件加密密钥 | `xxxxxxxx` |
| `LARK_VERIFICATION_TOKEN` | ✅ | 飞书验证 Token | `xxxxxxxx` |
| `ALERT_BOT_IDS` | ✅ | 告警机器人 ID | `cli_xxxxxxxx,cli_yyyyyyyy` |
| `LLM_PROVIDER` | ✅ | LLM 提供商 | `anthropic` 或 `openai` |
| `LLM_API_KEY` | ✅ | LLM API 密钥 | `sk-xxxxxxxx` |
| `LLM_BASE_URL` | ❌ | 自定义 LLM 端点 | `https://api.example.com` |
| `LLM_MODEL` | ❌ | 指定模型 | `claude-3-5-sonnet-20241022` |
| `LOG_LEVEL` | ❌ | 日志级别 | `info` |

---

## 附录 B: 快速启动脚本

```bash
#!/bin/bash
# quick-start.sh - 一键启动开发环境

set -e

echo "🚀 开始部署 ai-fixer..."

# 1. 检查依赖
echo "📦 检查依赖..."
command -v docker >/dev/null 2>&1 || { echo "❌ 需要安装 Docker"; exit 1; }

# 2. 配置环境变量
if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件填入配置后重新运行此脚本"
    exit 0
fi

# 3. 启动服务
echo "🐳 启动 Docker 服务..."
docker run -d \
  --name ai-fixer \
  -p 8080:8080 \
  --env-file .env \
  hahtangtang/ai-fixer:latest

# 4. 等待服务就绪
echo "⏳ 等待服务就绪..."
sleep 5

# 5. 执行迁移
echo "🗃️  执行数据库迁移..."
docker exec ai-fixer alembic upgrade head

# 6. 完成
echo "✅ 部署完成！"
echo ""
echo "访问地址: http://localhost:8080"
echo "API 文档: http://localhost:8080/docs"
echo ""
echo "常用命令:"
echo "  查看日志: docker logs -f ai-fixer"
echo "  停止服务: docker stop ai-fixer"
echo "  重启服务: docker restart ai-fixer"
```

---

**文档版本**: v2.0.0
**最后更新**: 2026-06-27
**维护者**: ai-fixer 团队

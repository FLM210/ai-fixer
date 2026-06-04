# 配置指南

ai-fixer 采用两层配置架构：

- **环境变量**：基础设施凭证，启动时必需，不可通过前端修改
- **数据库配置**：运行时参数，可通过前端管理页面修改，实时生效

## 环境变量（.env）

仅需配置基础设施连接：

```env
# 必填：PostgreSQL 连接串
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# 必填：Redis 连接
REDIS_URL=redis://localhost:6379/0
```

## 运行时配置（前端管理）

访问 http://localhost:5173/config 管理以下配置：

### LLM 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `llm_provider` | anthropic | LLM 提供商（anthropic / openai） |
| `llm_base_url` | - | LLM API 地址 |
| `llm_api_key` | - | LLM API 密钥（加密存储） |
| `llm_model` | - | 模型名称 |
| `llm_timeout_seconds` | 60 | 请求超时（秒） |
| `llm_max_turns` | 16 | 最大对话轮数 |

### 飞书集成

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `lark_app_id` | - | 飞书应用 App ID |
| `lark_app_secret` | - | 飞书应用 App Secret（加密存储） |
| `alert_bot_ids` | - | 告警机器人 Sender ID（逗号分隔） |
| `card_signing_key` | - | 卡片签名密钥（加密存储） |

### 安全围栏

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `fence_auto_namespaces` | default,staging | 允许自动修复的命名空间 |
| `fence_max_replica_change` | 5 | 单次最大副本数变更 |
| `fence_max_auto_fixes_per_hour` | 10 | 每小时最大自动修复次数 |
| `fence_max_auto_steps_per_incident` | 3 | 每个 incident 最大自动步数 |
| `fence_cooldown_seconds` | 300 | 冷却时间（秒） |
| `fence_require_approval_verbs` | delete,drain,cordon | 需审批的操作 |

### 诊断配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `diagnose_confidence_threshold` | 0.7 | 置信度阈值，低于此值触发工具排查 |

### 监控开关

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `pg_monitor_enabled` | false | 启用 PostgreSQL 监控 |
| `redis_monitor_enabled` | false | 启用 Redis 监控 |
| `aws_enabled` | false | 启用 AWS 监控 |

## 环境上下文

访问 http://localhost:5173/environment 配置生产环境信息。

环境上下文帮助 LLM 更准确地诊断问题。建议包含：

### 服务列表

```markdown
## 服务列表
- payment-service: 支付核心服务，3 副本，namespace=production，资源限制 2Gi/2CPU
- order-service: 订单服务，5 副本，namespace=production
- api-gateway: API 网关，2 副本，namespace=staging
```

### 基础设施

```markdown
## 基础设施
- K8s 集群: prod-cluster-1 (3 master + 10 worker)
- 节点配置: 16C32G
- 数据库: PostgreSQL 14 on RDS
- Redis: ElastiCache r6g.large, 3 节点集群
```

### 告警规则

```markdown
## 严重程度说明
- P0: 服务完全不可用，影响所有用户
- P1: 服务部分不可用，影响超过 30% 用户
- P2: 性能下降，响应时间超过 3 秒
- P3: 预警，资源使用率超过 80%
```

### 常见问题

```markdown
## 常见问题处理
- PodCrashLoopBackOff: 通常是 OOM，先检查内存限制
- HighCPUUsage: 检查是否有新版本发布或流量激增
- NodeNotReady: 检查节点磁盘、内存压力
```

### Shell 命令参考

```markdown
## Shell 命令参考
- 查看容器: docker ps -a
- 查看日志: docker logs --tail 100 <container>
- 检查磁盘: df -h
- 检查内存: free -m
- 网络诊断: curl -s http://localhost:<port>/health
```

## 配置优先级

```
数据库配置 > 环境变量默认值
```

数据库配置在启动时加载，覆盖环境变量中的默认值。修改数据库配置后实时生效，无需重启。

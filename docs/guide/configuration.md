# 配置管理

了解 ai-fixer 的配置管理机制。

## 配置架构

ai-fixer 采用两层配置架构：

```
┌─────────────────────────────────────────────────────────┐
│                    配置架构                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              环境变量（基础设施）                │   │
│  │    DATABASE_URL, REDIS_URL, LLM_API_KEY         │   │
│  │    启动时加载，不可通过前端修改                  │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │              数据库配置（运行时参数）            │   │
│  │    LLM_MODEL, ALERT_BOT_IDS, 安全围栏参数       │   │
│  │    前端可修改，热更新，优先级高于环境变量        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 环境变量配置

### .env 文件

```bash
# 基础设施（启动时必需）
DATABASE_URL=postgresql+asyncpg://fixer:fixer@localhost:5432/fixer
REDIS_URL=redis://localhost:6379/0

# 以下配置均通过前端管理页面设置，无需在此配置：
# - LLM 参数（provider, base_url, api_key, model）
# - 飞书集成（app_id, app_secret, alert_bot_ids）
# - 安全围栏参数
# - 监控开关
# - Embedding 配置
# - 日志级别
```

### 环境变量列表

| 变量名 | 必需 | 说明 | 示例值 |
|-------|------|------|--------|
| `DATABASE_URL` | ✅ | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | Redis 连接串 | `redis://localhost:6379/0` |

## 数据库配置

通过前端管理页面动态配置，支持热更新。

### LLM 配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `anthropic` |
| `LLM_API_KEY` | API 密钥 | - |
| `LLM_MODEL` | 模型名称 | `claude-3-5-sonnet-20241022` |
| `LLM_BASE_URL` | 自定义端点 | `https://api.anthropic.com` |
| `LLM_TIMEOUT` | 超时时间（秒） | `300` |

### 飞书配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `LARK_APP_ID` | 应用 ID | - |
| `LARK_APP_SECRET` | 应用密钥 | - |
| `ALERT_BOT_IDS` | 告警机器人 ID | - |

### 安全围栏配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `ALLOWED_NAMESPACES` | 允许的命名空间 | `default,production` |
| `MAX_REPLICA_CHANGE` | 最大副本变更比例 | `0.5` |
| `FORBIDDEN_VERBS` | 禁止的命令 | `rm -rf,drop table` |
| `HOURLY_QUOTA` | 每小时配额 | `10` |

### 监控配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `ENABLE_POSTGRESQL` | 启用 PostgreSQL 监控 | `true` |
| `ENABLE_REDIS` | 启用 Redis 监控 | `true` |
| `ENABLE_AWS` | 启用 AWS 监控 | `false` |

### Embedding 配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `EMBEDDING_PROVIDER` | Embedding 提供商 | `openai` |
| `EMBEDDING_MODEL` | 模型名称 | `text-embedding-3-small` |
| `EMBEDDING_API_KEY` | API 密钥 | - |

### 日志配置

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `LOG_LEVEL` | 日志级别 | `info` |

## 前端配置管理

### 访问配置页面

1. 打开前端管理页面：http://localhost:5173
2. 点击左侧菜单「配置」
3. 查看和修改配置

### 配置分组

配置按功能分组显示：

- **LLM 配置**：LLM 提供商、模型、API Key
- **飞书集成**：应用 ID、告警机器人 ID
- **安全围栏**：命名空间白名单、配额
- **监控开关**：各监控模块开关
- **其他**：日志级别等

### 修改配置

1. 在配置页面找到要修改的配置项
2. 修改值
3. 点击「保存」按钮
4. 配置立即生效（无需重启）

## 配置优先级

```
环境变量（.env） < 数据库配置（前端修改）
```

- 数据库配置优先级高于环境变量
- 如果数据库中没有配置，使用环境变量的值
- 前端修改后立即保存到数据库

## 配置热更新

数据库配置支持热更新：

1. **LLM 配置**：立即生效，下一次 LLM 调用使用新配置
2. **飞书配置**：立即生效，下一次消息处理使用新配置
3. **安全围栏**：立即生效，下一次策略评估使用新配置
4. **监控开关**：立即生效，下次检查使用新配置

## 配置 API

### 获取配置

```bash
curl http://localhost:8080/api/config
```

响应：

```json
{
  "success": true,
  "data": {
    "llm": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "base_url": "https://api.anthropic.com",
      "timeout": 300
    },
    "feishu": {
      "app_id": "cli_xxxxxxxx",
      "alert_bot_ids": ["cli_xxxxxxxx", "cli_yyyyyyyy"]
    },
    "security": {
      "allowed_namespaces": ["default", "production"],
      "max_replica_change": 0.5,
      "forbidden_verbs": ["rm -rf", "drop table"],
      "hourly_quota": 10
    }
  }
}
```

### 更新配置

```bash
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "LLM_MODEL": "claude-3-5-sonnet-20241022",
    "LLM_TIMEOUT": 600
  }'
```

## 配置存储

### 数据库表

配置存储在 `system_configs` 表中：

```sql
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 配置缓存

- 内存缓存：配置读取后缓存 5 分钟
- Redis 缓存：分布式环境共享配置
- 数据库：最终数据源

## 配置验证

### 输入验证

配置修改时进行验证：

```python
def validate_config(key: str, value: Any) -> bool:
    """验证配置值"""
    validators = {
        "LLM_PROVIDER": lambda v: v in ["anthropic", "openai"],
        "LLM_TIMEOUT": lambda v: isinstance(v, int) and v > 0,
        "HOURLY_QUOTA": lambda v: isinstance(v, int) and v > 0,
    }

    if key in validators:
        return validators[key](value)

    return True  # 未知配置项不做验证
```

### 类型检查

- 字符串：`str`
- 整数：`int`
- 布尔值：`bool`
- 列表：`list`
- JSON：`dict`

## 环境上下文

### 什么是环境上下文

环境上下文是用户配置的生产环境信息，LLM 在诊断时会参考：

- 服务列表及依赖关系
- 基础设施信息（集群、节点、数据库）
- 告警严重程度定义
- 常见问题处理方式

### 配置环境上下文

访问 http://localhost:5173/environment 配置：

```json
{
  "services": [
    {
      "name": "user-service",
      "namespace": "production",
      "dependencies": ["postgres", "redis"],
      "description": "用户服务"
    }
  ],
  "infrastructure": {
    "cluster": "prod-cluster",
    "nodes": 10,
    "databases": ["postgres", "mysql"]
  },
  "alert_definitions": {
    "critical": "影响用户访问的严重问题",
    "warning": "需要关注但不影响用户"
  }
}
```

### 使用方式

1. LLM 诊断时自动加载环境上下文
2. 根据服务依赖关系判断问题影响范围
3. 参考历史处理方式生成修复方案

## 最佳实践

### 1. 敏感信息管理

- API Key 等敏感信息不提交到代码库
- 使用 `.env` 文件管理本地开发配置
- 使用 Secret 管理生产环境配置

### 2. 配置备份

定期备份数据库配置：

```bash
# 导出配置
curl http://localhost:8080/api/config > config_backup.json

# 导入配置
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d @config_backup.json
```

### 3. 配置文档

记录配置变更：

```bash
# 配置变更日志
- 2024-01-15: 更新 LLM 模型为 claude-3-5-sonnet-20241022
- 2024-01-14: 添加 production 命名空间到白名单
- 2024-01-13: 增加每小时配额到 20
```

## 故障排查

### 配置不生效

```bash
# 检查数据库配置
curl http://localhost:8080/api/config

# 检查环境变量
docker-compose exec app env | grep LLM

# 检查日志
docker-compose logs app | grep config
```

### 配置丢失

```bash
# 检查数据库连接
docker-compose exec postgres psql -U fixer -d fixer -c "SELECT * FROM system_configs;"

# 恢复配置
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d @config_backup.json
```

## 下一步

- [管理后台](/guide/dashboard) - 前端配置管理
- [API 文档](/api/) - 配置 API 接口
- [开发指南](/development/) - 配置开发

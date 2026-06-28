# API 概览

ai-fixer 提供 RESTful API 和 Webhook 接口。

## API 端点

### 系统状态

| 端点 | 方法 | 说明 |
|------|------|------|
| `/healthz` | GET | 健康检查 |
| `/metrics` | GET | Prometheus 指标 |
| `/api/status` | GET | 系统状态概览 |

### Incident 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/incidents` | GET | Incident 列表 |
| `/api/incidents/{id}` | GET | Incident 详情 |
| `/api/incidents/{id}/events` | GET | Incident 事件时间线 |

### 配置管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 获取所有配置 |
| `/api/config` | PUT | 更新配置 |

### 插件管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/plugins` | GET | 插件列表 |
| `/api/plugins/{name}` | GET | 插件详情 |

### 告警接收

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/alert` | POST | 接收告警触发工作流 |

### 知识库

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/knowledge` | GET | 知识条目列表 |
| `/api/knowledge` | POST | 创建知识条目 |
| `/api/knowledge/{id}` | GET | 知识条目详情 |
| `/api/knowledge/{id}` | PUT | 更新知识条目 |
| `/api/knowledge/{id}` | DELETE | 删除知识条目 |

### 环境上下文

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/environment-context` | GET | 获取环境上下文 |
| `/api/environment-context` | PUT | 更新环境上下文 |

### 事件流

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/events` | GET | SSE 实时事件流 |

### 飞书集成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/lark/event` | POST | 飞书事件回调 |
| `/lark/card/action` | POST | 卡片按钮回调 |

## 认证方式

### API Key 认证

部分 API 需要 API Key 认证：

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8080/api/incidents
```

### 飞书事件签名

飞书回调使用签名验证：

```python
# 验证签名
def verify_signature(timestamp: str, nonce: str, body: str, signature: str) -> bool:
    expected = hashlib.sha256(
        f"{timestamp}{nonce}{ENCRYPT_KEY}{body}".encode()
    ).hexdigest()
    return expected == signature
```

## 响应格式

### 成功响应

```json
{
  "success": true,
  "data": {
    // 响应数据
  },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": [
      {
        "field": "name",
        "message": "不能为空"
      }
    ]
  }
}
```

### 分页响应

```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `UNAUTHORIZED` | 401 | 未认证 |
| `FORBIDDEN` | 403 | 无权限 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 资源冲突 |
| `INTERNAL_ERROR` | 500 | 内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 使用示例

### 获取 Incident 列表

```bash
curl http://localhost:8080/api/incidents?page=1&page_size=20&status=diagnosing
```

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "INC-20240115-001",
        "title": "Pod CrashLoopBackOff",
        "status": "diagnosing",
        "created_at": "2024-01-15T10:30:00Z",
        "severity": "high"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20
  }
}
```

### 获取 Incident 详情

```bash
curl http://localhost:8080/api/incidents/INC-20240115-001
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "INC-20240115-001",
    "title": "Pod CrashLoopBackOff",
    "status": "resolved",
    "diagnosis": {
      "conclusion": "OOMKilled",
      "confidence": 0.95,
      "key_findings": [...]
    },
    "proposal": {
      "description": "增加内存限制",
      "risk_level": "medium",
      "steps": [...]
    },
    "execution_result": {
      "success": true,
      "duration": 92
    },
    "events": [...]
  }
}
```

### 更新配置

```bash
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "LLM_PROVIDER": "anthropic",
    "LLM_MODEL": "claude-3-5-sonnet-20241022"
  }'
```

### 手动触发告警

```bash
curl -X POST http://localhost:8080/api/alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": "[告警] Pod CrashLoopBackOff\n服务: user-service\n命名空间: production",
    "sender_id": "alert_bot"
  }'
```

### 订阅实时事件

```bash
curl -N http://localhost:8080/api/events
```

SSE 事件流格式：

```
event: incident_created
data: {"id":"INC-20240115-001","title":"Pod CrashLoopBackOff"}

event: diagnosis_completed
data: {"incident_id":"INC-20240115-001","conclusion":"OOMKilled"}

event: execution_completed
data: {"incident_id":"INC-20240115-001","success":true}
```

## SDK 和客户端

### Python SDK

```python
from ai_fixer import AIFixerClient

client = AIFixerClient(base_url="http://localhost:8080")

# 获取 Incident 列表
incidents = await client.incidents.list(status="diagnosing")

# 获取 Incident 详情
incident = await client.incidents.get("INC-20240115-001")

# 更新配置
await client.config.update({"LLM_MODEL": "claude-3-5-sonnet-20241022"})
```

### cURL 脚本

```bash
#!/bin/bash

BASE_URL="http://localhost:8080"

# 获取系统状态
curl "$BASE_URL/api/status" | jq

# 获取 Incident 列表
curl "$BASE_URL/api/incidents?page=1&page_size=10" | jq

# 获取 Incident 详情
curl "$BASE_URL/api/incidents/$1" | jq
```

## API 文档

交互式 API 文档：

- **Swagger UI**：http://localhost:8080/docs
- **ReDoc**：http://localhost:8080/redoc

## 下一步

- [REST API](/api/rest) - 详细 API 参考
- [Webhook](/api/webhook) - Webhook 配置
- [开发指南](/development/) - 集成开发

# Webhook 配置

配置 Webhook 接收告警和通知。

## 飞书 Webhook

### 事件订阅

配置飞书事件订阅接收消息。

**端点：** `https://your-domain.com/lark/event`

**支持事件：**

| 事件类型 | 说明 |
|---------|------|
| `im.message.receive_v1` | 接收消息 |
| `im.message.reaction.created_v1` | 消息表情回复 |

**配置步骤：**

1. 登录飞书开放平台
2. 进入应用 → 「事件订阅」
3. 配置请求地址
4. 添加事件

### 卡片回调

配置卡片按钮回调。

**端点：** `https://your-domain.com/lark/card/action`

**回调数据：**

```json
{
  "action": {
    "value": {
      "action": "confirm_diagnosis",
      "incident_id": "INC-20240115-001"
    }
  },
  "open_id": "ou_xxxxxxxx",
  "token": "xxxxxxxx"
}
```

## Prometheus Alertmanager Webhook

### 配置 Alertmanager

在 `alertmanager.yml` 中配置 Webhook：

```yaml
receivers:
  - name: ai-fixer
    webhook_configs:
      - url: 'https://your-domain.com/api/alert'
        send_resolved: false
        http_config:
          basic_auth:
            username: 'your_username'
            password: 'your_password'

route:
  receiver: ai-fixer
  group_by: ['alertname', 'namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  match:
    severity: critical
```

### 接收格式

ai-fixer 接收标准 Alertmanager webhook 格式：

```json
{
  "version": "4",
  "groupKey": "...",
  "status": "firing",
  "receiver": "ai-fixer",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "PodCrashLooping",
        "namespace": "production",
        "pod": "user-service-abc123",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Pod CrashLoopBackOff",
        "description": "Pod user-service-abc123 is in CrashLoopBackOff state"
      },
      "startsAt": "2024-01-15T10:30:00Z",
      "fingerprint": "abc123def456"
    }
  ]
}
```

## Grafana Webhook

### 配置 Grafana

在 Grafana 中配置告警通知：

1. 进入 Alerting → Contact points
2. 添加新的 Contact point
3. 选择 Webhook 类型
4. 配置 URL：`https://your-domain.com/api/alert`

### 接收格式

```json
{
  "title": "Pod CrashLoopBackOff",
  "state": "alerting",
  "message": "Pod user-service-abc123 is in CrashLoopBackOff state",
  "ruleId": 1,
  "ruleName": "Pod CrashLoopBackOff",
  "ruleUrl": "https://grafana.example.com/alerting/1/edit",
  "orgId": 1,
  "dashboardId": 1,
  "panelId": 1,
  "tags": {
    "namespace": "production",
    "pod": "user-service-abc123"
  },
  "evalMatches": [
    {
      "value": 5,
      "metric": "restarts",
      "tags": {
        "namespace": "production",
        "pod": "user-service-abc123"
      }
    }
  ]
}
```

## 自定义 Webhook

### 接收格式

ai-fixer 支持自定义 Webhook 格式：

```json
{
  "message": "[告警] Pod CrashLoopBackOff\n服务: user-service\n命名空间: production",
  "sender_id": "custom_alert_bot",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "source": "custom_monitoring",
    "severity": "high"
  }
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 告警消息内容 |
| `sender_id` | string | 否 | 发送者 ID |
| `chat_id` | string | 否 | 群组 ID |
| `timestamp` | string | 否 | 时间戳 |
| `metadata` | object | 否 | 附加元数据 |

### 配置步骤

1. 确保 `sender_id` 在 `ALERT_BOT_IDS` 白名单中
2. 发送 POST 请求到 `/api/alert`
3. 等待处理结果

## Webhook 安全

### 签名验证

飞书 Webhook 使用签名验证：

```python
import hashlib

def verify_signature(
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
    encrypt_key: str,
) -> bool:
    """验证飞书签名"""
    content = f"{timestamp}{nonce}{encrypt_key}{body}"
    expected = hashlib.sha256(content.encode()).hexdigest()
    return expected == signature
```

### API Key 认证

自定义 Webhook 可使用 API Key 认证：

```bash
curl -X POST https://your-domain.com/api/alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "message": "Test alert",
    "sender_id": "custom_bot"
  }'
```

### IP 白名单

限制允许的 IP 地址：

```python
ALLOWED_IPS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
]

@app.middleware("http")
async def ip_whitelist(request, call_next):
    client_ip = request.client.host
    if not is_ip_allowed(client_ip, ALLOWED_IPS):
        return JSONResponse(
            status_code=403,
            content={"error": "IP not allowed"},
        )
    return await call_next(request)
```

## 测试 Webhook

### 使用 cURL

```bash
# 测试告警接收
curl -X POST http://localhost:8080/api/alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": "[告警] 测试告警\n服务: test-service",
    "sender_id": "test_bot"
  }'

# 测试飞书事件
curl -X POST http://localhost:8080/lark/event \
  -H "Content-Type: application/json" \
  -H "X-Lark-Signature: test_signature" \
  -d '{
    "type": "event_callback",
    "event": {
      "message": {
        "content": "{\"text\":\"@ai_fixer /help\"}",
        "sender": {"sender_id": {"open_id": "ou_xxxxxxxx"}}
      }
    }
  }'
```

### 使用 Python

```python
import httpx
import asyncio

async def test_webhook():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/alert",
            json={
                "message": "[告警] 测试告警\n服务: test-service",
                "sender_id": "test_bot",
            },
        )
        print(response.json())

asyncio.run(test_webhook())
```

## 常见问题

### Webhook 未触发

1. 检查 URL 是否正确
2. 检查网络连通性
3. 查看服务日志
4. 验证签名配置

### 消息未处理

1. 检查 `sender_id` 是否在白名单
2. 检查消息格式是否正确
3. 查看告警检测日志

### 处理失败

1. 检查 LLM 配置
2. 检查插件状态
3. 查看错误日志

## 下一步

- [API 概览](/api/) - API 总览
- [REST API](/api/rest) - 详细 API 参考
- [告警处理](/guide/alerts) - 告警处理流程

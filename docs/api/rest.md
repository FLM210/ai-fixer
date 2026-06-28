# REST API 详细参考

详细的 REST API 接口文档。

## 系统状态

### GET /healthz

健康检查端点。

**响应示例：**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600
}
```

### GET /metrics

Prometheus 指标端点。

**响应格式：** Prometheus exposition format

### GET /api/status

系统状态概览。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "status": "running",
    "version": "1.0.0",
    "uptime": 3600,
    "active_incidents": 5,
    "pending_approvals": 2,
    "plugins_loaded": 25,
    "llm_status": "connected",
    "database_status": "connected",
    "redis_status": "connected"
  }
}
```

## Incident 管理

### GET /api/incidents

获取 Incident 列表。

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `page` | integer | 否 | 页码（默认 1） |
| `page_size` | integer | 否 | 每页数量（默认 20） |
| `status` | string | 否 | 状态筛选 |
| `severity` | string | 否 | 严重程度筛选 |
| `start_date` | string | 否 | 开始日期 |
| `end_date` | string | 否 | 结束日期 |
| `search` | string | 否 | 搜索关键词 |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "INC-20240115-001",
        "title": "Pod CrashLoopBackOff",
        "status": "resolved",
        "severity": "high",
        "category": "kubernetes",
        "created_at": "2024-01-15T10:30:00Z",
        "resolved_at": "2024-01-15T10:35:00Z",
        "duration": 300
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

### GET /api/incidents/:id

获取 Incident 详情。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | string | Incident ID |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "INC-20240115-001",
    "title": "Pod CrashLoopBackOff",
    "status": "resolved",
    "severity": "high",
    "category": "kubernetes",
    "description": "生产环境 Pod 持续重启",
    "source": "alert_bot",
    "fingerprint": "abc123def456",
    "diagnosis": {
      "conclusion": "OOMKilled",
      "confidence": 0.95,
      "key_findings": [
        "容器内存使用达到 limit",
        "最近一次重启原因是 OOMKilled",
        "应用日志显示内存泄漏"
      ],
      "suggested_actions": [
        "增加内存 limit",
        "检查应用内存泄漏"
      ],
      "diagnosed_at": "2024-01-15T10:31:00Z"
    },
    "proposal": {
      "description": "增加 Pod 内存限制并重启",
      "steps": [
        "修改 deployment 的 memory limit 为 512Mi",
        "重启 Pod"
      ],
      "risk_level": "medium",
      "estimated_duration": "2 分钟",
      "rollback_plan": "回滚到原始配置",
      "proposed_at": "2024-01-15T10:32:00Z"
    },
    "execution_result": {
      "success": true,
      "duration": 92,
      "executed_at": "2024-01-15T10:33:00Z",
      "output": "Deployment updated successfully"
    },
    "events": [
      {
        "type": "alert_received",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {...}
      },
      {
        "type": "diagnosis_completed",
        "timestamp": "2024-01-15T10:31:00Z",
        "data": {...}
      }
    ],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  }
}
```

### GET /api/incidents/:id/events

获取 Incident 事件时间线。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": "evt_001",
        "type": "alert_received",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {
          "message": "[告警] Pod CrashLoopBackOff",
          "sender_id": "alert_bot"
        }
      },
      {
        "id": "evt_002",
        "type": "diagnosis_started",
        "timestamp": "2024-01-15T10:30:05Z",
        "data": {}
      },
      {
        "id": "evt_003",
        "type": "tool_call",
        "timestamp": "2024-01-15T10:30:10Z",
        "data": {
          "tool": "describe_pod",
          "parameters": {"pod_name": "user-service-abc123"},
          "result": {...}
        }
      },
      {
        "id": "evt_004",
        "type": "diagnosis_completed",
        "timestamp": "2024-01-15T10:31:00Z",
        "data": {
          "conclusion": "OOMKilled",
          "confidence": 0.95
        }
      }
    ]
  }
}
```

## 配置管理

### GET /api/config

获取所有配置。

**响应示例：**

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
    },
    "monitoring": {
      "enable_postgresql": true,
      "enable_redis": true,
      "enable_aws": false
    }
  }
}
```

### PUT /api/config

更新配置。

**请求体：**

```json
{
  "LLM_MODEL": "claude-3-5-sonnet-20241022",
  "LLM_TIMEOUT": 600
}
```

**响应示例：**

```json
{
  "success": true,
  "message": "配置更新成功"
}
```

## 插件管理

### GET /api/plugins

获取插件列表。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "plugins": [
      {
        "name": "list_pods",
        "description": "列出 Pod",
        "category": "diagnostic",
        "parameters": {
          "type": "object",
          "properties": {
            "namespace": {"type": "string"},
            "label": {"type": "string"}
          }
        }
      },
      {
        "name": "restart_pod",
        "description": "重启 Pod",
        "category": "remediation",
        "parameters": {
          "type": "object",
          "properties": {
            "pod_name": {"type": "string"},
            "namespace": {"type": "string"}
          }
        }
      }
    ],
    "total": 25,
    "diagnostic": 15,
    "remediation": 10
  }
}
```

### GET /api/plugins/:name

获取插件详情。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "name": "list_pods",
    "description": "列出 Pod",
    "category": "diagnostic",
    "parameters": {
      "type": "object",
      "properties": {
        "namespace": {
          "type": "string",
          "description": "命名空间",
          "default": "default"
        },
        "label": {
          "type": "string",
          "description": "标签选择器"
        }
      }
    },
    "usage_count": 150,
    "avg_duration": 2.5,
    "success_rate": 0.98
  }
}
```

## 告警接收

### POST /api/alert

接收告警触发工作流。

**请求体：**

```json
{
  "message": "[告警] Pod CrashLoopBackOff\n服务: user-service\n命名空间: production",
  "sender_id": "alert_bot",
  "chat_id": "oc_xxxxxxxx",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "incident_id": "INC-20240115-001",
    "status": "accepted",
    "message": "告警已接收，开始处理"
  }
}
```

## 知识库

### GET /api/knowledge

获取知识条目列表。

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | integer | 页码 |
| `page_size` | integer | 每页数量 |
| `category` | string | 分类筛选 |
| `search` | string | 搜索关键词 |

### POST /api/knowledge

创建知识条目。

**请求体：**

```json
{
  "title": "Pod OOMKilled 处理方案",
  "content": "当 Pod 因 OOMKilled 重启时...",
  "category": "kubernetes",
  "tags": ["pod", "oom", "memory"]
}
```

### GET /api/knowledge/:id

获取知识条目详情。

### PUT /api/knowledge/:id

更新知识条目。

### DELETE /api/knowledge/:id

删除知识条目。

## 环境上下文

### GET /api/environment-context

获取环境上下文。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "services": [
      {
        "name": "user-service",
        "namespace": "production",
        "dependencies": ["postgres", "redis"]
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
}
```

### PUT /api/environment-context

更新环境上下文。

## 事件流

### GET /api/events

SSE 实时事件流。

**响应格式：**

```
event: incident_created
data: {"id":"INC-20240115-001","title":"Pod CrashLoopBackOff","severity":"high"}

event: diagnosis_completed
data: {"incident_id":"INC-20240115-001","conclusion":"OOMKilled","confidence":0.95}

event: proposal_created
data: {"incident_id":"INC-20240115-001","risk_level":"medium"}

event: execution_completed
data: {"incident_id":"INC-20240115-001","success":true,"duration":92}

event: incident_resolved
data: {"incident_id":"INC-20240115-001","resolution":"fixed"}
```

## 飞书集成

### POST /lark/event

飞书事件回调端点。

**请求头：**

```
Content-Type: application/json
X-Lark-Signature: xxxxxxxx
X-Lark-Request-Timestamp: 1234567890
X-Lark-Request-Nonce: xxxxxxxx
```

### POST /lark/card/action

卡片按钮回调端点。

**请求体：**

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

## 错误处理

### 400 Bad Request

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": [
      {
        "field": "page",
        "message": "必须是正整数"
      }
    ]
  }
}
```

### 401 Unauthorized

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "未认证"
  }
}
```

### 404 Not Found

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Incident 不存在"
  }
}
```

### 500 Internal Server Error

```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "服务器内部错误"
  }
}
```

## 下一步

- [API 概览](/api/) - API 总览
- [Webhook](/api/webhook) - Webhook 配置
- [开发指南](/development/) - 集成开发

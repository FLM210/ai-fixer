# API 参考

ai-fixer 提供 RESTful API，所有端点以 `/api` 为前缀。

## 系统状态

### GET /api/status

获取系统概览状态。

**响应**

```json
{
  "version": "0.1.0",
  "uptime_healthy": true,
  "health": {
    "db": "ok",
    "redis": "ok"
  },
  "active_incidents": 3,
  "total_incidents": 42,
  "plugin_count": 27,
  "dynamic_config_loaded": true,
  "llm_provider": "anthropic",
  "llm_model": "claude-sonnet-4-6"
}
```

### GET /healthz

健康检查。

**响应**

```json
{
  "status": "ok",
  "checks": {
    "db": {"status": "ok"},
    "llm": {"status": "ok", "provider": "anthropic", "model": "claude-sonnet-4-6"}
  }
}
```

### GET /metrics

Prometheus 格式的监控指标。

## 告警接收

### POST /api/alert

接收告警，触发 LLM 工作流。

**请求**

```json
{
  "text": "🔴 Firing\n\n告警名称: PodCrashLoopBackOff\n严重程度: P0\n服务: payment-service\n详情: Pod OOMKilled",
  "source": "api"
}
```

**响应**

```json
{
  "incident_id": "uuid",
  "status": "resolved",
  "triage": {
    "category": "内存溢出",
    "severity": "p0",
    "service": "payment-service"
  },
  "diagnosis": {
    "summary": "根因分析...",
    "confidence": 0.8,
    "evidence": {},
    "similar_incidents": []
  },
  "proposals": [
    {
      "plugin_name": "k8s.restart_pod",
      "description": "重启 Pod",
      "risk_level": "medium",
      "args": {}
    }
  ],
  "llm_turns": [
    {
      "phase": "triage",
      "turn_index": 0,
      "role": "user",
      "content": "..."
    }
  ],
  "execution_results": [],
  "raw_workflow_state": {}
}
```

## Incidents

### GET /api/incidents

获取 Incident 列表。

**参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页数量（最大 100） |
| `status` | string | - | 状态筛选 |
| `severity` | string | - | 严重程度筛选 |

**响应**

```json
{
  "items": [
    {
      "id": "uuid",
      "status": "resolved",
      "category": "内存溢出",
      "severity": "p0",
      "service": "payment-service",
      "summary": "...",
      "created_at": "2024-01-01T00:00:00Z",
      "confidence": 0.8,
      "proposal_count": 1
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### GET /api/incidents/{id}

获取 Incident 详情，包含完整的诊断信息、修复建议和 LLM 对话记录。

## 配置管理

### GET /api/config

获取所有可配置项（分组）。

**响应**

```json
{
  "groups": [
    {
      "name": "llm",
      "label": "LLM 模型",
      "items": {
        "llm_provider": {
          "value": "anthropic",
          "type": "str",
          "description": "LLM 提供商",
          "is_secret": false,
          "source": "database"
        }
      }
    }
  ]
}
```

### PUT /api/config

批量更新配置。

**请求**

```json
{
  "configs": {
    "llm_model": "claude-sonnet-4-6",
    "diagnose_confidence_threshold": 0.8
  },
  "updated_by": "admin"
}
```

## 插件管理

### GET /api/plugins

获取所有插件列表。

**响应**

```json
[
  {
    "name": "k8s.describe_pod",
    "category": "diagnostic",
    "resource_type": "k8s",
    "risk_level": "low",
    "timeout_seconds": 30,
    "description": "获取 Pod 详情",
    "enabled": true,
    "source": "builtin",
    "input_schema": {}
  }
]
```

### PUT /api/plugins/{name}/toggle

启用/禁用插件。

**请求**

```json
{
  "enabled": false
}
```

### POST /api/plugins/reload

热重载所有插件。

### POST /api/plugins/upload

上传自定义插件文件。

**请求**：`multipart/form-data`，字段 `file` 为 `.py` 文件。

### DELETE /api/plugins/custom/{name}

删除自定义插件。

## 环境上下文

### GET /api/environment-context

获取环境上下文。

### PUT /api/environment-context

更新环境上下文。

**请求**

```json
{
  "content": "# 生产环境信息\n\n## 服务列表\n...",
  "updated_by": "admin"
}
```

## 事件流

### GET /api/events

SSE（Server-Sent Events）实时事件流。

**事件类型**

| 事件 | 说明 |
|------|------|
| `connected` | 连接建立 |
| `incident_update` | Incident 状态变更 |
| `config_update` | 配置变更 |

**示例**

```
event: connected
data: {"time": "2024-01-01T00:00:00Z"}

event: incident_update
data: {"incident_id": "uuid", "status": "resolved"}
```

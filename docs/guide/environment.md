# 环境上下文配置

配置生产环境信息，帮助 LLM 更准确地诊断问题。

## 什么是环境上下文

环境上下文是用户配置的生产环境信息，LLM 在诊断时会参考这些信息：

- **服务列表**：所有微服务及其依赖关系
- **基础设施**：集群、节点、数据库信息
- **告警定义**：不同严重程度的定义
- **常见问题**：历史问题的处理方式

## 配置位置

访问 http://localhost:5173/environment 配置环境上下文。

## 配置结构

### 服务列表

```json
{
  "services": [
    {
      "name": "user-service",
      "namespace": "production",
      "description": "用户服务，处理用户注册、登录、信息管理",
      "dependencies": ["postgres", "redis", "kafka"],
      "team": "platform",
      "oncall": "user@example.com"
    },
    {
      "name": "order-service",
      "namespace": "production",
      "description": "订单服务，处理订单创建、支付、状态管理",
      "dependencies": ["postgres", "redis", "user-service", "payment-service"],
      "team": "business",
      "oncall": "order@example.com"
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 服务名称 |
| `namespace` | string | ✅ | Kubernetes 命名空间 |
| `description` | string | ❌ | 服务描述 |
| `dependencies` | array | ❌ | 依赖的服务列表 |
| `team` | string | ❌ | 负责团队 |
| `oncall` | string | ❌ | 值班联系人 |

### 基础设施信息

```json
{
  "infrastructure": {
    "cluster": "prod-cluster",
    "region": "cn-hangzhou",
    "nodes": 10,
    "databases": [
      {
        "name": "postgres",
        "type": "PostgreSQL",
        "version": "14",
        "host": "postgres.example.com",
        "databases": ["user_db", "order_db"]
      },
      {
        "name": "redis",
        "type": "Redis",
        "version": "7.0",
        "host": "redis.example.com",
        "databases": [0, 1, 2]
      }
    ],
    "middleware": [
      {
        "name": "kafka",
        "type": "Kafka",
        "version": "3.5",
        "brokers": ["kafka-1:9092", "kafka-2:9092", "kafka-3:9092"]
      }
    ]
  }
}
```

### 告警严重程度定义

```json
{
  "alert_definitions": {
    "critical": {
      "description": "影响用户访问的严重问题",
      "response_time": "5 分钟",
      "examples": [
        "核心服务完全不可用",
        "数据库主节点故障",
        "支付服务异常"
      ]
    },
    "warning": {
      "description": "需要关注但不影响用户",
      "response_time": "30 分钟",
      "examples": [
        "服务延迟升高",
        "磁盘使用率超过 80%",
        "非核心服务异常"
      ]
    },
    "info": {
      "description": "仅供参考",
      "response_time": "24 小时",
      "examples": [
        "服务部署完成",
        "配置变更通知",
        "定时任务完成"
      ]
    }
  }
}
```

### 常见问题处理

```json
{
  "common_issues": [
    {
      "issue": "Pod CrashLoopBackOff",
      "category": "kubernetes",
      "description": "Pod 持续重启",
      "common_causes": [
        "OOMKilled（内存不足）",
        "应用启动失败",
        "健康检查失败",
        "依赖服务不可用"
      ],
      "standard_procedure": [
        "1. 查看 Pod 日志：kubectl logs <pod-name> --previous",
        "2. 查看 Pod 事件：kubectl describe pod <pod-name>",
        "3. 检查资源使用：kubectl top pod <pod-name>",
        "4. 检查依赖服务状态"
      ]
    },
    {
      "issue": "数据库连接数过高",
      "category": "database",
      "description": "数据库连接数接近或超过限制",
      "common_causes": [
        "连接泄漏",
        "并发请求过多",
        "连接池配置不当"
      ],
      "standard_procedure": [
        "1. 查看当前连接数：SELECT count(*) FROM pg_stat_activity;",
        "2. 查看连接来源：SELECT client_addr, count(*) FROM pg_stat_activity GROUP BY client_addr;",
        "3. 终止空闲连接：SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';",
        "4. 检查应用连接池配置"
      ]
    }
  ]
}
```

## 使用场景

### 1. 告警诊断

LLM 诊断时会参考：

- 服务依赖关系，判断问题影响范围
- 常见问题处理方式，快速定位问题
- 值班联系人，自动通知相关人员

**示例：**

```
告警：user-service Pod CrashLoopBackOff

LLM 诊断：
- 根据环境上下文，user-service 依赖 postgres 和 redis
- 检查 postgres 和 redis 状态
- 参考常见问题处理方式，优先检查 OOMKilled
- 如果需要升级，通知 user@example.com
```

### 2. 修复方案生成

LLM 生成修复方案时会参考：

- 集群信息，确定可用资源
- 命名空间限制，避免误操作
- 历史处理方式，生成标准方案

### 3. 影响评估

LLM 评估问题影响时会参考：

- 服务依赖关系，判断影响范围
- 告警严重程度定义，确定优先级
- 响应时间要求，安排处理顺序

## 配置示例

### 完整配置示例

```json
{
  "services": [
    {
      "name": "api-gateway",
      "namespace": "production",
      "description": "API 网关，所有请求入口",
      "dependencies": ["user-service", "order-service", "product-service"],
      "team": "platform",
      "oncall": "platform@example.com"
    },
    {
      "name": "user-service",
      "namespace": "production",
      "description": "用户服务",
      "dependencies": ["postgres", "redis"],
      "team": "platform",
      "oncall": "platform@example.com"
    },
    {
      "name": "order-service",
      "namespace": "production",
      "description": "订单服务",
      "dependencies": ["postgres", "redis", "kafka", "user-service", "payment-service"],
      "team": "business",
      "oncall": "business@example.com"
    },
    {
      "name": "payment-service",
      "namespace": "production",
      "description": "支付服务",
      "dependencies": ["postgres", "redis"],
      "team": "business",
      "oncall": "business@example.com"
    }
  ],
  "infrastructure": {
    "cluster": "prod-cluster",
    "region": "cn-hangzhou",
    "nodes": 10,
    "databases": [
      {
        "name": "postgres",
        "type": "PostgreSQL",
        "version": "14",
        "host": "postgres.example.com",
        "databases": ["user_db", "order_db", "payment_db"]
      }
    ]
  },
  "alert_definitions": {
    "critical": {
      "description": "影响用户访问",
      "response_time": "5 分钟"
    },
    "warning": {
      "description": "不影响用户",
      "response_time": "30 分钟"
    }
  }
}
```

## 最佳实践

### 1. 保持更新

- 服务变更时及时更新环境上下文
- 定期审查配置准确性
- 自动化配置更新（可选）

### 2. 详细描述

- 为每个服务添加清晰的描述
- 记录关键依赖关系
- 添加值班联系人

### 3. 分层管理

- 按团队或服务分组管理
- 使用命名空间区分环境
- 定期备份配置

## API 接口

### 获取环境上下文

```bash
curl http://localhost:8080/api/environment-context
```

### 更新环境上下文

```bash
curl -X PUT http://localhost:8080/api/environment-context \
  -H "Content-Type: application/json" \
  -d @environment-context.json
```

## 故障排查

### 配置不生效

```bash
# 检查配置是否保存
curl http://localhost:8080/api/environment-context

# 检查 LLM 是否加载
docker-compose logs app | grep "environment"
```

### 配置格式错误

```bash
# 验证 JSON 格式
cat environment-context.json | jq .

# 检查必填字段
jq '.services[] | select(.name == null)' environment-context.json
```

## 下一步

- [核心概念](/guide/concepts) - 了解 LLM 诊断流程
- [告警处理](/guide/alerts) - 了解告警处理流程
- [配置管理](/guide/configuration) - 其他配置项

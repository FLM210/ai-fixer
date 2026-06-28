# 生产环境加固

安全配置、监控和备份策略。

> **重要**：ai-fixer 只负责应用本身，PostgreSQL 和 Redis 作为独立的基础设施服务，请参考各自文档进行安全加固和备份。

## 安全配置

### 1. 密钥管理

#### 生成强密钥

```bash
# 生成 API Key
openssl rand -hex 32

# 生成飞书加密密钥
openssl rand -hex 32

# 生成卡片签名密钥
openssl rand -hex 32
```

#### 使用 Secret 管理

**Kubernetes：**

```bash
kubectl create secret generic ai-fixer-secrets \
  --from-literal=database-url='postgresql+asyncpg://user:STRONG_PASSWORD@postgres:5432/fixer' \
  --from-literal=redis-url='redis://:STRONG_PASSWORD@redis:6379/0' \
  --from-literal=llm-api-key='sk-...' \
  --from-literal=lark-app-secret='...' \
  -n ai-fixer
```

**Docker：**

使用 `.env` 文件，并确保权限：

```bash
chmod 600 .env
```

### 2. 网络安全

#### 启用 HTTPS

使用 Nginx 反向代理：

```nginx
server {
    listen 443 ssl;
    server_name ai-fixer.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/ai-fixer.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai-fixer.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 配置防火墙

```bash
# 只允许必要的端口
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -j DROP
```

### 3. 认证授权

#### 飞书签名验证

应用自动验证飞书事件签名，确保请求来源可信。

#### API Key 认证（可选）

如需对外暴露 API，建议启用 API Key 认证。

### 4. 日志安全

#### 日志脱敏

应用自动对敏感信息进行脱敏处理：
- API Key
- 数据库密码
- 飞书 App Secret

#### 日志轮转

```yaml
# docker-compose.yml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 监控配置

### 1. Prometheus 指标

应用暴露以下指标：

```python
# 请求指标
http_requests_total
http_request_duration_seconds

# 工作流指标
workflow_runs_total
workflow_run_duration_seconds
workflow_pending_count

# LLM 指标
llm_requests_total
llm_request_duration_seconds
llm_tokens_total

# 插件指标
plugin_executions_total
plugin_execution_duration_seconds
```

### 2. Grafana Dashboard

导入预置 Dashboard：

```bash
# Dashboard JSON 文件
deploy/grafana/k8s-fixer-overview.json
```

**Dashboard 包含：**
- 系统状态概览
- 请求速率和延迟
- 工作流执行统计
- LLM 调用统计
- 插件执行统计
- 错误率和异常

### 3. 告警规则

```yaml
# prometheus-rules.yaml
groups:
  - name: ai-fixer
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率"

      - alert: WorkflowPendingTimeout
        expr: workflow_pending_count > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "待处理工作流过多"

      - alert: LLMServiceDown
        expr: llm_requests_total{status="error"} / llm_requests_total > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "LLM 服务异常"
```

### 4. 健康检查

```python
# /healthz 端点
@app.get("/healthz")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "llm": await check_llm(),
    }

    all_healthy = all(checks.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
    }
```

## 性能优化

### 1. 应用优化

```bash
# Worker 数量（根据 CPU 核心数）
WORKERS=4

# 请求超时
REQUEST_TIMEOUT=300

# LLM 超时
LLM_TIMEOUT=300
```

### 2. 连接池配置

应用自动管理数据库连接池，可通过环境变量调整：

```bash
# 数据库连接池大小
DB_POOL_SIZE=20

# 最大溢出连接数
DB_MAX_OVERFLOW=10
```

## 灾难恢复

### 1. 恢复计划

**RTO（恢复时间目标）：** 30 分钟
**RPO（恢复点目标）：** 1 小时

### 2. 恢复流程

1. **评估损失**
   - 检查数据完整性
   - 确定恢复时间点

2. **恢复基础设施**
   - 恢复 PostgreSQL（参考数据库文档）
   - 恢复 Redis（参考 Redis 文档）

3. **启动应用**
   - 执行数据库迁移
   - 启动应用服务

4. **验证恢复**
   - 检查健康状态
   - 测试功能

### 3. 恢复演练

```bash
# 每月进行一次恢复演练
# 1. 在测试环境恢复备份
# 2. 验证数据完整性
# 3. 测试应用功能
# 4. 记录恢复时间
```

## 安全审计

### 1. 审计日志

应用自动记录关键操作：
- 告警接收
- 诊断执行
- 修复执行
- 配置变更

### 2. 定期安全检查

```bash
# 检查容器漏洞
trivy image hahtangtang/ai-fixer:latest

# 检查依赖漏洞
pip audit
```

### 3. 访问控制

```yaml
# 限制 API 访问
rate_limit:
  enabled: true
  requests_per_minute: 100
  burst: 20
```

## 合规性

### 1. 数据保留

应用自动清理过期数据：
- Incident 记录保留 90 天
- 超时工作流自动清理

### 2. 数据导出

```bash
# 导出 Incident 数据
curl http://localhost:8080/api/incidents?format=csv > incidents.csv
```

### 3. 隐私保护

- 日志脱敏
- 数据加密传输
- 访问控制
- 审计日志

## 下一步

- [部署概览](/deployment/) - 部署方式选择
- [Kubernetes 部署](/deployment/kubernetes) - K8s 部署
- [开发指南](/development/) - 本地开发

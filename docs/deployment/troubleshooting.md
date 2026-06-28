# 故障排查

常见问题和解决方法。

## 服务启动问题

### 1. 数据库连接失败

**症状：**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**可能原因：**
- PostgreSQL 未启动
- 连接串配置错误
- 网络问题

**解决方法：**

```bash
# 1. 检查 DATABASE_URL 配置
docker exec ai-fixer env | grep DATABASE_URL

# 2. 测试网络连通性
ping your-postgres-host

# 3. 测试数据库连接
docker exec ai-fixer python -c "import asyncpg; print('asyncpg ok')"

# 4. 检查 PostgreSQL 是否可访问
psql -h your-postgres-host -U fixer -d fixer -c "SELECT 1;"
```

### 2. Redis 连接失败

**症状：**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方法：**

```bash
# 1. 检查 REDIS_URL 配置
docker exec ai-fixer env | grep REDIS_URL

# 2. 测试网络连通性
ping your-redis-host

# 3. 测试 Redis 连接
redis-cli -h your-redis-host ping

# 4. 检查密码是否正确
redis-cli -h your-redis-host -a your_password ping
```

### 3. 端口冲突

**症状：**
```
Error starting userland proxy: Bind for 0.0.0.0:8080 failed: port is already allocated
```

**解决方法：**

```bash
# 1. 检查端口占用
lsof -i :8080

# 2. 停止占用进程
kill -9 <PID>

# 3. 或修改端口映射
docker run -d -p 9000:8080 hahtangtang/ai-fixer:latest
```

### 4. pgvector 扩展未安装

**症状：**
```
psycopg2.errors.UndefinedObject: type "vector" does not exist
```

**解决方法：**

```bash
# 连接到 PostgreSQL 安装扩展
psql -h your-postgres-host -U fixer -d fixer -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -h your-postgres-host -U fixer -d fixer -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# 验证
psql -h your-postgres-host -U fixer -d fixer -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

## 飞书集成问题

### 1. 机器人不响应

**症状：** 在群组中 @机器人无响应

**可能原因：**
- 机器人未添加到群组
- 权限未审批
- 事件订阅未配置

**解决方法：**

```bash
# 1. 检查机器人是否添加到群组
# 在群设置 → 群机器人中查看

# 2. 检查权限审批状态
# 飞书开放平台 → 权限管理

# 3. 检查事件订阅
# 飞书开放平台 → 事件订阅

# 4. 查看日志
docker logs ai-fixer | grep -i "lark\|feishu"
```

### 2. 消息发送失败

**症状：** 机器人无法发送消息

**可能原因：**
- App ID 或 App Secret 错误
- 权限不足
- 网络问题

**解决方法：**

```bash
# 1. 检查配置
docker exec ai-fixer env | grep LARK

# 2. 测试 API 连通性
curl -I https://open.feishu.cn

# 3. 查看错误日志
docker logs ai-fixer | grep -i "error\|exception"
```

### 3. 事件订阅验证失败

**症状：** 飞书事件订阅配置失败

**可能原因：**
- 公网地址不可访问
- HTTPS 证书问题
- Encrypt Key 配置错误

**解决方法：**

```bash
# 1. 检查公网地址
curl https://your-domain.com/healthz

# 2. 检查 HTTPS 证书
openssl s_client -connect your-domain.com:443

# 3. 验证 Encrypt Key
docker exec ai-fixer env | grep LARK_ENCRYPT_KEY
```

### 4. 卡片按钮无响应

**症状：** 点击卡片按钮无反应

**可能原因：**
- 卡片回调地址未配置
- 签名验证失败
- 网络问题

**解决方法：**

```bash
# 1. 检查卡片回调配置
# 飞书开放平台 → 消息卡片 → 请求地址

# 2. 查看日志
docker logs ai-fixer | grep "card\|action"
```

## LLM 问题

### 1. LLM API 调用失败

**症状：**
```
openai.error.AuthenticationError: Invalid API Key
```

**解决方法：**

```bash
# 1. 检查 API Key
docker exec ai-fixer env | grep LLM_API_KEY

# 2. 测试 API 连通性
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $LLM_API_KEY" \
  -H "anthropic-version: 2023-06-01"

# 3. 检查配置
curl http://localhost:8080/api/config | jq '.llm'
```

### 2. LLM 响应超时

**症状：**
```
httpx.ReadTimeout: timed out
```

**解决方法：**

```bash
# 1. 增加超时时间
# 前端配置 → LLM_TIMEOUT = 600

# 2. 检查网络
ping api.anthropic.com

# 3. 查看日志
docker logs ai-fixer | grep "timeout"
```

### 3. LLM 响应格式错误

**症状：**
```
json.JSONDecodeError: Expecting value
```

**解决方法：**

```bash
# 1. 查看 LLM 原始响应
docker logs ai-fixer | grep "llm.response"

# 2. 检查模型配置
curl http://localhost:8080/api/config | jq '.llm.model'

# 3. 尝试其他模型
# 前端配置 → 切换模型
```

## 插件问题

### 1. 插件未加载

**症状：** `/plugins` 命令显示插件数量为 0

**解决方法：**

```bash
# 1. 检查插件目录
ls app/plugins/builtin/

# 2. 查看日志
docker logs ai-fixer | grep "plugin"

# 3. 检查注册
curl http://localhost:8080/api/plugins
```

### 2. 插件执行失败

**症状：** 插件调用返回错误

**解决方法：**

```bash
# 1. 查看 Incident 详情
curl http://localhost:8080/api/incidents/{id} | jq '.events[] | select(.type == "tool_call")'

# 2. 查看插件日志
docker logs ai-fixer | grep "plugin.execute"

# 3. 测试插件
# 使用 API 直接调用插件
```

### 3. K8s 插件权限不足

**症状：**
```
kubernetes.client.exceptions.ApiException: (403) Forbidden
```

**解决方法：**

```bash
# 1. 检查 ServiceAccount
kubectl get serviceaccount ai-fixer -n ai-fixer

# 2. 检查 RBAC
kubectl get clusterrole ai-fixer -o yaml
kubectl get clusterrolebinding ai-fixer -o yaml

# 3. 测试权限
kubectl auth can-i list pods -n production --as=system:serviceaccount:ai-fixer:ai-fixer
```

## 工作流问题

### 1. 工作流卡住

**症状：** Incident 长时间处于 pending 状态

**解决方法：**

```bash
# 1. 查看工作流状态
docker logs ai-fixer | grep "workflow"

# 2. 检查 interrupt 状态
curl http://localhost:8080/api/incidents/{id} | jq '.status'

# 3. 手动清理超时工作流
# 系统会自动清理 1 小时未响应的工作流
```

### 2. 诊断确认超时

**症状：** 诊断确认卡片发送后 1 小时未响应

**解决方法：**

```bash
# 1. 查看超时日志
docker logs ai-fixer | grep "timeout"

# 2. 检查飞书消息是否发送成功
# 在飞书群中查看是否有卡片

# 3. 手动触发新工作流
curl -X POST http://localhost:8080/api/alert \
  -H "Content-Type: application/json" \
  -d '{"message": "重试告警", "sender_id": "test"}'
```

### 3. 执行失败

**症状：** 修复执行失败

**解决方法：**

```bash
# 1. 查看执行详情
curl http://localhost:8080/api/incidents/{id} | jq '.execution_result'

# 2. 查看错误日志
docker logs ai-fixer | grep "execute\|error"

# 3. 检查权限
kubectl auth can-i patch deployment -n production
```

## 前端问题

### 1. 页面无法访问

**症状：** 浏览器无法打开 http://localhost:8080

**解决方法：**

```bash
# 1. 检查服务是否运行
docker ps

# 2. 检查端口
lsof -i :8080

# 3. 查看日志
docker logs ai-fixer

# 4. 重新构建前端
make build-ui
```

### 2. API 请求失败

**症状：** 前端显示网络错误

**解决方法：**

```bash
# 1. 检查后端服务
curl http://localhost:8080/healthz

# 2. 查看浏览器控制台错误
# F12 → Console
```

### 3. 刷新页面 404

**症状：** 刷新非首页页面显示 404

**原因：** SPA 路由问题

**解决方法：**

```bash
# 确保后端配置了 SPA fallback
# 检查 app/main.py 中的静态文件配置
```

## 性能问题

### 1. 响应缓慢

**症状：** API 响应时间长

**解决方法：**

```bash
# 1. 检查资源使用
docker stats ai-fixer

# 2. 查看慢查询
# 检查 PostgreSQL 慢查询日志

# 3. 调整配置
# 增加 WORKERS、DB_POOL_SIZE
```

### 2. 内存不足

**症状：** 容器 OOMKilled

**解决方法：**

```bash
# 1. 检查内存使用
docker stats ai-fixer

# 2. 调整资源限制
docker run -d --memory=2g hahtangtang/ai-fixer:latest

# 3. 检查内存泄漏
# 查看 Python 内存使用
```

## 日志分析

### 查看实时日志

```bash
# Docker
docker logs -f ai-fixer

# Kubernetes
kubectl logs -f deployment/ai-fixer -n ai-fixer
```

### 搜索错误

```bash
# 搜索错误
docker logs ai-fixer | grep -i "error\|exception\|traceback"

# 搜索特定模块
docker logs ai-fixer | grep "lark\|plugin\|workflow"
```

### 查看特定时间段

```bash
# 查看最近 1 小时
docker logs --since 1h ai-fixer

# 查看特定时间
docker logs --since "2024-01-15T10:00:00" ai-fixer
```

## 获取帮助

### 1. 收集信息

```bash
# 系统信息
docker version
uname -a

# 服务状态
docker ps

# 日志
docker logs ai-fixer > app.log 2>&1
```

### 2. 提交 Issue

在 GitHub 上提交 Issue，包含：

- 问题描述
- 复现步骤
- 错误日志
- 环境信息

### 3. 社区支持

- GitHub Discussions
- 飞书群（如果配置了）

## 下一步

- [部署概览](/deployment/) - 部署方式选择
- [开发指南](/development/) - 本地开发调试
- [贡献指南](/development/contributing) - 报告问题

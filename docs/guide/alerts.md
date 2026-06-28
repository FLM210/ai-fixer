# 告警处理

了解 ai-fixer 的告警处理流程。

## 告警接收

### 告警来源

- **Prometheus Alertmanager**：通过飞书 Webhook 发送
- **自定义告警机器人**：发送到飞书群并 @ai-fixer
- **手动触发**：通过飞书命令 `/diag` 或 API

### 告警消息格式

```plaintext
@ai-fixer [告警] 生产环境 Pod CrashLoopBackOff

服务: user-service
命名空间: production
Pod: user-service-abc123
状态: CrashLoopBackOff
重启次数: 5
时间: 2024-01-15 10:30:00
```

### 告警检测

`AlertDetector` 通过以下方式识别告警：

1. **Sender ID 白名单**：只处理 `ALERT_BOT_IDS` 中的机器人消息
2. **正则匹配**：识别告警关键词和格式
3. **@触发**：消息必须包含 @ai-fixer

## 处理流程

### 1. 告警分类（Triage）

LLM 对告警进行分类：

| 类别 | 示例 |
|------|------|
| kubernetes | Pod 异常、部署失败、资源问题 |
| database | 慢查询、锁等待、连接数过高 |
| middleware | Redis、Kafka、MQ 问题 |
| network | 网络延迟、连接超时 |
| application | 应用错误、性能问题 |

### 2. 去重检查

- 生成告警指纹（基于关键字段）
- 检查是否有相同指纹的活跃 Incident
- 重复告警直接跳过，避免重复处理

### 3. 诊断（Diagnose）

LLM 多轮 agent loop：

```
用户消息 → LLM 思考 → 调用插件 → 获取结果 → 继续思考 → ... → 输出诊断
```

#### 诊断插件调用示例

```json
{
  "tool": "describe_pod",
  "parameters": {
    "pod_name": "user-service-abc123",
    "namespace": "production"
  }
}
```

#### 诊断输出

```json
{
  "conclusion": "Pod 因 OOMKilled 重启",
  "confidence": 0.95,
  "key_findings": [
    "容器内存使用达到 limit",
    "最近一次重启原因是 OOMKilled",
    "应用日志显示内存泄漏"
  ],
  "suggested_actions": [
    "增加内存 limit",
    "检查应用内存泄漏"
  ]
}
```

### 4. 诊断确认

发送诊断确认卡片到飞书：

**卡片内容：**
- 诊断结论
- 置信度（百分比）
- 关键发现
- 建议操作

**用户操作：**
- ✅ 确认诊断：继续生成修复方案
- ❌ 拒绝诊断：升级到人工处理

### 5. 方案生成（Propose）

LLM 基于诊断结果生成修复方案：

```json
{
  "proposal": {
    "description": "增加 Pod 内存限制并重启",
    "steps": [
      "修改 deployment 的 memory limit 为 512Mi",
      "重启 Pod"
    ],
    "risk_level": "medium",
    "estimated_duration": "2 分钟",
    "rollback_plan": "回滚到原始配置"
  }
}
```

### 6. 安全策略评估（Policy Evaluate）

`ExecutionPolicy` 评估方案：

```python
if risk_level == "critical":
    return "escalate"  # 始终升级
elif risk_level in ["low", "medium"]:
    if within_fence(quota_ok):
        return "auto_execute"
    else:
        return "require_approval"
else:
    return "require_approval"
```

### 7. 方案确认

发送方案确认卡片：

**卡片内容：**
- 方案描述
- 执行步骤
- 风险等级
- 预估耗时
- 回滚方案

**用户操作：**
- ✅ 确认执行：开始执行修复
- ❌ 拒绝方案：升级到人工处理

### 8. 执行修复（Execute）

调用修复插件执行方案：

```json
{
  "tool": "scale_deployment",
  "parameters": {
    "deployment": "user-service",
    "namespace": "production",
    "replicas": 3
  }
}
```

### 9. 验证结果（Verify）

执行后验证修复效果：

```python
# 检查 Pod 状态
pods = await list_pods(namespace="production", label="app=user-service")
all_running = all(pod.status == "Running" for pod in pods)

if all_running:
    return "resolved"
else:
    return "escalate"
```

### 10. 结果通知

发送执行结果卡片：

**成功示例：**
```plaintext
✅ 修复成功

Incident: INC-20240115-001
操作: 增加内存限制并重启
耗时: 1 分 32 秒
结果: 所有 Pod 正常运行
```

**失败示例：**
```plaintext
❌ 修复失败

Incident: INC-20240115-001
操作: 增加内存限制并重启
错误: 权限不足，无法修改 deployment
建议: 升级到人工处理
```

## 飞书命令

### 查看状态

```
@ai-fixer /status
```

返回：
```plaintext
系统状态：正常
活跃 Incident：3
今日处理：12
成功率：91.7%
```

### 查看插件

```
@ai-fixer /plugins
```

返回：
```plaintext
可用插件：

诊断插件：
- list_pods: 列出 Pod
- describe_pod: 查看 Pod 详情
- slow_queries: 查询慢查询

修复插件：
- restart_pod: 重启 Pod
- scale_deployment: 扩缩容
```

### 手动诊断

```
@ai-fixer /diag
```

对当前消息触发诊断流程。

### 忽略告警

```
@ai-fixer /ignore
```

忽略当前告警，不进行处理。

### 升级处理

```
@ai-fixer /escalate
```

升级当前 Incident 到人工处理。

## 配置调整

### 告警白名单

在前端配置 `ALERT_BOT_IDS`：

```bash
ALERT_BOT_IDS=cli_xxxxxxxx,cli_yyyyyyyy
```

### 超时配置

```bash
# 诊断超时（秒）
DIAGNOSIS_TIMEOUT=300

# 方案生成超时（秒）
PROPOSAL_TIMEOUT=60

# 审批超时（秒）
APPROVAL_TIMEOUT=3600
```

### 重试配置

```bash
# LLM 重试次数
LLM_MAX_RETRIES=3

# 插件重试次数
PLUGIN_MAX_RETRIES=2
```

## 故障排查

### 告警未触发

```bash
# 检查告警机器人 ID 配置
docker-compose exec app env | grep ALERT_BOT_IDS

# 检查日志
docker-compose logs app | grep -i "alert"

# 检查消息是否被识别
docker-compose logs app | grep "AlertDetector"
```

### 诊断失败

```bash
# 检查 LLM 配置
docker-compose exec app env | grep LLM

# 查看诊断日志
docker-compose logs app | grep "diagnose"

# 查看插件调用
docker-compose logs app | grep "plugin"
```

### 执行失败

```bash
# 检查权限
kubectl auth can-i patch deployment -n production

# 查看执行日志
docker-compose logs app | grep "execute"

# 检查安全围栏
docker-compose exec app env | grep FENCE
```

## 下一步

- [插件系统](/guide/plugins) - 了解和开发插件
- [核心概念](/guide/concepts) - 深入了解工作流
- [故障排查](/deployment/troubleshooting) - 常见问题解决

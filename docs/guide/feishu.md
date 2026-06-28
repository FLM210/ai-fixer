# 飞书集成

配置飞书机器人，实现告警接收和交互。

## 创建飞书应用

### 1. 登录飞书开放平台

访问 [飞书开放平台](https://open.feishu.cn/)，使用企业账号登录。

### 2. 创建企业自建应用

1. 点击「创建企业自建应用」
2. 填写应用信息：
   - **应用名称**: `ai-fixer`（或自定义名称）
   - **应用描述**: 智能运维修复助手
   - **应用图标**: 上传合适的图标

### 3. 启用机器人能力

1. 进入应用详情页 → 「应用能力」→「机器人」
2. 点击「启用机器人」
3. 记录 `App ID` 和 `App Secret`

## 配置权限

进入「权限管理」页面，申请以下权限：

### 消息相关权限（必需）

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取与发送单聊消息 | `im:message` | 接收和发送消息 |
| 获取群组消息 | `im:message.group_at_msg` | 接收群组 @消息 |
| 获取用户发给机器人的单聊消息 | `im:message.p2p_msg` | 接收单聊消息 |
| 读取消息内容 | `im:message:readonly` | 读取消息详情 |
| 发送消息 | `im:message:send_as_bot` | 发送消息 |

### 卡片相关权限（必需）

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 创建交互卡片 | `im:message.interactive` | 发送交互卡片 |

### 群组相关权限（可选）

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取群组信息 | `im:chat:readonly` | 获取群组详情 |

## 获取加密配置

1. 进入「事件订阅」页面
2. 记录以下信息：
   - **Verification Token**: 用于验证请求来源
   - **Encrypt Key**: 用于解密事件数据

## 配置环境变量

在 `.env` 文件中添加：

```bash
# 飞书应用凭证
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 事件加密配置
LARK_ENCRYPT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LARK_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 告警机器人 ID（逗号分隔）
ALERT_BOT_IDS=cli_xxxxxxxx,cli_yyyyyyyy
```

## 配置事件订阅

### 1. 获取公网地址

部署完成后，获取应用的公网访问地址，如 `https://ai-fixer.your-domain.com`

### 2. 配置请求地址

1. 返回飞书开放平台 → ai-fixer 应用
2. 进入「事件订阅」页面
3. 配置请求地址：`https://ai-fixer.your-domain.com/lark/event`
4. 添加事件：
   - `im.message.receive_v1` - 接收消息
   - `im.message.reaction.created_v1` - 消息表情回复（可选）

## 添加机器人到群组

1. 在飞书中创建或进入告警群组
2. 点击群设置 → 「群机器人」→「添加机器人」
3. 搜索并添加 `ai-fixer` 机器人
4. 记录机器人的 `open_id`（格式：`ou_xxxxxxxx`）

## 告警触发配置

### 告警消息格式

为了让告警消息触发 ai-fixer，需要在告警消息中 @ai-fixer 机器人：

```
@ai-fixer [告警] 生产环境 Pod CrashLoopBackOff

服务: user-service
命名空间: production
Pod: user-service-abc123
状态: CrashLoopBackOff
重启次数: 5
```

### Prometheus Alertmanager 配置

```yaml
receivers:
  - name: ai-fixer
    webhook_configs:
      - url: 'http://your-feishu-bot/send'
        send_resolved: false

route:
  receiver: ai-fixer
  match:
    severity: critical
```

### 自定义告警机器人

如果使用自定义告警机器人，需要：

1. 在告警消息中包含 `@ai-fixer` 或机器人的 `open_id`
2. 确保告警机器人的 `sender_id` 在 `ALERT_BOT_IDS` 白名单中

## 飞书命令

机器人支持以下命令：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/status` | 查看系统状态 |
| `/plugins` | 查看可用插件 |
| `/diag` | 手动触发诊断 |
| `/run` | 手动执行修复 |
| `/ignore` | 忽略当前告警 |
| `/escalate` | 升级到人工处理 |

## 测试飞书集成

### 1. 测试机器人响应

在群组中发送：

```
@ai-fixer /help
```

期望响应：

```
可用命令：
/status - 查看系统状态
/plugins - 查看可用插件
/diag - 手动触发诊断
/help - 显示帮助信息
```

### 2. 测试告警处理

发送模拟告警：

```
@ai-fixer [告警] 测试告警 - Pod Restart
命名空间: default
Pod: test-pod-abc123
状态: CrashLoopBackOff
```

期望行为：
- 收到诊断确认卡片
- 点击「确认」后收到修复方案卡片
- 点击「执行」后收到执行结果

## 故障排查

### 机器人不响应

```bash
# 1. 检查应用日志
docker-compose logs -f app | grep -i "lark\|feishu"

# 2. 检查环境变量
docker-compose exec app env | grep LARK

# 3. 检查网络连通性
curl -I https://open.feishu.cn
```

### 事件订阅失败

1. 确认公网地址可访问
2. 检查 HTTPS 证书是否有效
3. 验证 Encrypt Key 和 Verification Token 配置正确

### 消息发送失败

1. 检查机器人是否已添加到群组
2. 确认机器人有发送消息的权限
3. 查看日志中的错误信息

## 下一步

- [告警处理](/guide/alerts) - 了解告警处理流程
- [插件系统](/guide/plugins) - 扩展诊断和修复能力
- [部署指南](/deployment/) - 生产环境部署

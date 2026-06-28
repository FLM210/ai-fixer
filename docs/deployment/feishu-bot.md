# 飞书机器人创建

从零开始创建飞书机器人应用。

## 步骤 1：登录飞书开放平台

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 使用企业管理员账号登录
3. 如果没有企业，需要先注册企业

## 步骤 2：创建企业自建应用

1. 点击「创建企业自建应用」
2. 填写应用信息：

| 字段 | 值 | 说明 |
|------|-----|------|
| 应用名称 | ai-fixer | 用户看到的机器人名称 |
| 应用描述 | 智能运维修复助手 | 简短描述 |
| 应用图标 | 上传图标 | 建议使用 120x120 PNG |

3. 点击「创建」

## 步骤 3：启用机器人能力

1. 进入应用详情页
2. 左侧菜单：「应用能力」→「机器人」
3. 点击「启用机器人」
4. 记录凭证信息：
   - **App ID**: `cli_xxxxxxxxxxxxxxxx`
   - **App Secret**: 点击「查看」获取

## 步骤 4：配置权限

进入「权限管理」页面，申请以下权限：

### 必需权限

#### 消息权限

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取与发送单聊消息 | `im:message` | 接收和发送单聊消息 |
| 获取群组消息 | `im:message.group_at_msg` | 接收群组 @消息 |
| 获取用户发给机器人的单聊消息 | `im:message.p2p_msg` | 接收单聊消息 |
| 读取消息内容 | `im:message:readonly` | 读取消息详情 |
| 发送消息 | `im:message:send_as_bot` | 机器人发送消息 |

#### 卡片权限

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 创建交互卡片 | `im:message.interactive` | 发送交互卡片 |

### 可选权限

#### 群组权限

| 权限名称 | 权限标识 | 用途 |
|---------|---------|------|
| 获取群组信息 | `im:chat:readonly` | 获取群组详情 |

### 申请权限

1. 点击每个权限右侧的「申请」按钮
2. 填写申请理由（如：用于接收告警消息并自动处理）
3. 等待管理员审批

## 步骤 5：获取加密配置

### 5.1 进入事件订阅页面

1. 左侧菜单：「事件订阅」
2. 记录以下信息：

| 配置项 | 说明 | 用途 |
|-------|------|------|
| Verification Token | 验证 Token | 验证请求来源 |
| Encrypt Key | 加密密钥 | 解密事件数据 |

### 5.2 配置请求地址（暂时跳过）

> 注意：需要先完成应用部署获取公网地址后再回来配置

请求地址格式：`https://your-domain.com/lark/event`

## 步骤 6：发布应用

### 6.1 创建版本

1. 左侧菜单：「版本管理与发布」
2. 点击「创建版本」
3. 填写版本号（如：1.0.0）和更新说明
4. 点击「保存」

### 6.2 提交审核

1. 点击「提交审核」
2. 等待管理员审核通过
3. 审核通过后应用自动发布

## 步骤 7：配置环境变量

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

## 步骤 8：添加机器人到群组

### 8.1 创建告警群组

1. 在飞书中创建新群组
2. 命名为「告警处理」或类似名称
3. 添加运维团队成员

### 8.2 添加机器人

1. 点击群设置（右上角「...」）
2. 选择「群机器人」→「添加机器人」
3. 搜索「ai-fixer」
4. 点击「添加」

### 8.3 记录机器人信息

添加后，记录机器人的 `open_id`：

1. 点击机器人头像
2. 查看「机器人信息」
3. 记录 `open_id`（格式：`ou_xxxxxxxx`）

## 步骤 9：配置告警机器人

### 9.1 获取告警机器人 App ID

如果使用其他飞书机器人发送告警：

1. 在飞书开放平台找到告警机器人应用
2. 进入应用详情 → 「凭证与基础信息」
3. 记录 `App ID`

### 9.2 配置白名单

在 `.env` 或前端配置中添加告警机器人 ID：

```bash
ALERT_BOT_IDS=cli_xxxxxxxx,cli_yyyyyyyy
```

多个 ID 用逗号分隔。

## 步骤 10：配置事件订阅

### 10.1 获取公网地址

部署完成后，获取应用的公网访问地址。

**Docker Compose：**
```bash
# 使用 ngrok 临时测试
ngrok http 8080

# 或使用正式域名
https://ai-fixer.your-domain.com
```

**Kubernetes：**
```bash
# 获取 Ingress 地址
kubectl get ingress -n ai-fixer
```

### 10.2 配置请求地址

1. 返回飞书开放平台 → ai-fixer 应用
2. 进入「事件订阅」页面
3. 配置请求地址：`https://your-domain.com/lark/event`
4. 点击「验证」按钮

### 10.3 添加事件

1. 点击「添加事件」
2. 搜索并添加：
   - `im.message.receive_v1` - 接收消息
   - `im.message.reaction.created_v1` - 消息表情回复（可选）
3. 保存配置

## 验证配置

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

## 常见问题

### 1. 机器人不响应

**可能原因：**
- 机器人未添加到群组
- 权限未审批
- 事件订阅未配置

**解决方法：**
1. 检查机器人是否已添加到群组
2. 检查权限审批状态
3. 检查事件订阅配置

### 2. 权限申请被拒绝

**可能原因：**
- 申请理由不充分
- 企业安全策略限制

**解决方法：**
1. 详细说明使用场景
2. 联系企业管理员

### 3. 事件订阅验证失败

**可能原因：**
- 公网地址不可访问
- HTTPS 证书问题
- Encrypt Key 配置错误

**解决方法：**
1. 检查公网地址是否可访问
2. 验证 HTTPS 证书
3. 确认 Encrypt Key 配置正确

## 下一步

- [基础设施准备](/deployment/infrastructure) - 准备数据库和 Redis
- [Docker 部署](/deployment/docker) - Docker Compose 部署
- [Kubernetes 部署](/deployment/kubernetes) - K8s 部署

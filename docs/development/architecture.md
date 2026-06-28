# 架构设计

深入了解 ai-fixer 的系统架构。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      飞书群聊界面                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ 告警消息 │  │ /命令   │  │ 卡片按钮 │  │ 结果通知 │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
└───────┼────────────┼────────────┼────────────┼──────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    飞书集成层 (app/lark/)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ LarkClient  │  │ AlertDetector│  │ CardRenderer│         │
│  │ WebSocket   │  │ 告警检测     │  │ 卡片渲染    │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph 工作流引擎                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ingest → triage → diagnose                         │   │
│  │    → send_diagnosis_card                            │   │
│  │    → await_diagnosis_approval (interrupt)           │   │
│  │    → propose → policy_evaluate                      │   │
│  │    → send_proposal_card                             │   │
│  │    → await_proposal_approval (interrupt)            │   │
│  │    → execute → verify → resolve/escalate            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              WorkflowRunManager                      │   │
│  │    管理 interrupt/resume、超时清理                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                     核心服务层                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ LLM 层    │  │ 插件系统  │  │ 执行策略  │               │
│  │ Anthropic │  │ diagnostic│  │ 安全围栏  │               │
│  │ OpenAI    │  │ remediat. │  │ 配额管理  │               │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘               │
└────────┼──────────────┼──────────────┼─────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ PostgreSQL│  │   Redis   │  │ pgvector  │               │
│  │ 持久化    │  │ 锁/去重   │  │ 向量记忆  │               │
│  └───────────┘  └───────────┘  └───────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 飞书集成层 (`app/lark/`)

负责与飞书平台的交互：

#### LarkClient

```python
class LarkClient:
    """飞书 API 客户端"""

    async def start(self):
        """启动 WebSocket 长连接"""

    async def send_message(self, chat_id: str, content: dict):
        """发送消息"""

    async def send_card(self, chat_id: str, card: dict):
        """发送交互卡片"""

    async def reply_message(self, message_id: str, content: dict):
        """回复消息"""
```

#### AlertDetector

```python
class AlertDetector:
    """告警检测器"""

    def __init__(self, bot_ids: list[str]):
        self.bot_ids = bot_ids

    def is_alert(self, event: dict) -> bool:
        """判断是否为告警消息"""
        # 1. 检查 sender_id 是否在白名单
        # 2. 检查消息格式是否匹配告警模板
        # 3. 检查是否 @ai-fixer

    def parse_alert(self, event: dict) -> Alert:
        """解析告警消息"""
```

#### CardRenderer

```python
class CardRenderer:
    """卡片渲染器"""

    def render_diagnosis_card(self, diagnosis: Diagnosis) -> dict:
        """渲染诊断确认卡片"""

    def render_proposal_card(self, proposal: FixProposal) -> dict:
        """渲染方案确认卡片"""

    def render_result_card(self, result: ExecutionResult) -> dict:
        """渲染执行结果卡片"""
```

#### WorkflowRunManager

```python
class WorkflowRunManager:
    """工作流运行管理器"""

    async def create_run(self, incident_id: str) -> str:
        """创建新的工作流运行"""

    async def resume_run(self, run_id: str, user_input: dict):
        """恢复被 interrupt 的工作流"""

    async def cleanup_timeout_runs(self):
        """清理超时的 pending runs"""
```

### 2. LangGraph 工作流引擎 (`app/graph/`)

#### GraphState

```python
class GraphState(TypedDict):
    """工作流状态"""

    # 告警信息
    alert: Alert
    incident_id: str

    # 诊断相关
    diagnosis: Optional[Diagnosis]
    diagnosis_approved: Optional[bool]

    # 方案相关
    proposal: Optional[FixProposal]
    proposal_approved: Optional[bool]

    # 执行相关
    execution_result: Optional[ExecutionResult]

    # LLM 对话历史
    messages: list[Message]

    # 元数据
    metadata: dict
```

#### 工作流节点

```python
async def ingest(state: GraphState) -> GraphState:
    """接收和预处理告警"""

async def triage(state: GraphState) -> GraphState:
    """告警分类和去重"""

async def diagnose(state: GraphState) -> GraphState:
    """LLM 多轮诊断"""

async def send_diagnosis_card(state: GraphState) -> GraphState:
    """发送诊断确认卡片"""

async def await_diagnosis_approval(state: GraphState) -> GraphState:
    """等待诊断确认（interrupt）"""

async def propose(state: GraphState) -> GraphState:
    """生成修复方案"""

async def policy_evaluate(state: GraphState) -> GraphState:
    """安全策略评估"""

async def send_proposal_card(state: GraphState) -> GraphState:
    """发送方案确认卡片"""

async def await_proposal_approval(state: GraphState) -> GraphState:
    """等待方案确认（interrupt）"""

async def execute(state: GraphState) -> GraphState:
    """执行修复"""

async def verify(state: GraphState) -> GraphState:
    """验证修复结果"""

async def resolve(state: GraphState) -> GraphState:
    """标记问题已解决"""

async def escalate(state: GraphState) -> GraphState:
    """升级到人工处理"""
```

#### 条件边

```python
def should_skip(state: GraphState) -> str:
    """重复告警检查"""
    if is_duplicate(state["alert"]):
        return "end"
    return "continue"

def after_triage(state: GraphState) -> str:
    """triage 后路由"""
    if state.get("skip"):
        return "end"
    return "diagnose"

def after_diagnosis_approval(state: GraphState) -> str:
    """诊断确认后路由"""
    if state["diagnosis_approved"]:
        return "propose"
    return "escalate"

def after_policy_evaluate(state: GraphState) -> str:
    """策略评估后路由"""
    if state["requires_approval"]:
        return "send_proposal_card"
    return "execute"

def after_proposal_approval(state: GraphState) -> str:
    """方案确认后路由"""
    if state["proposal_approved"]:
        return "execute"
    return "escalate"

def after_verify(state: GraphState) -> str:
    """验证后路由"""
    if state["verification_passed"]:
        return "resolve"
    return "escalate"
```

### 3. LLM 层 (`app/llm/`)

#### LLMClient ABC

```python
class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[Tool]) -> Response:
        """多轮对话"""

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """单轮补全"""
```

#### AnthropicClient

```python
class AnthropicClient(LLMClient):
    """Anthropic Claude 实现"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages, tools):
        response = await self.client.messages.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        return response
```

#### OpenAIClient

```python
class OpenAIClient(LLMClient):
    """OpenAI GPT 实现"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def chat(self, messages, tools):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        return response
```

### 4. 插件系统 (`app/plugins/`)

#### Plugin ABC

```python
class Plugin(ABC):
    """插件抽象基类"""

    @property
    @abstractmethod
    def spec(self) -> PluginSpec:
        """插件规格"""

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """执行插件"""
```

#### PluginRegistry

```python
class PluginRegistry:
    """插件注册表"""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        """注册插件"""
        self._plugins[plugin.spec.name] = plugin

    def get(self, name: str) -> Optional[Plugin]:
        """获取插件"""

    def list_all(self) -> list[PluginSpec]:
        """列出所有插件"""

    def list_by_category(self, category: str) -> list[PluginSpec]:
        """按类别列出插件"""
```

#### 插件发现

```python
# 自动发现内置插件
import pkgutil
import importlib

def discover_plugins(package_path: str):
    """自动发现并加载插件"""
    for importer, modname, ispkg in pkgutil.iter_modules([package_path]):
        importlib.import_module(f"{package_path}.{modname}")
```

### 5. 执行策略引擎 (`app/engine/policy.py`)

```python
class ExecutionPolicy:
    """执行策略引擎"""

    def __init__(self, config: PolicyConfig):
        self.config = config

    async def evaluate(self, proposal: FixProposal) -> PolicyDecision:
        """
        评估修复方案

        Returns:
            PolicyDecision: {
                "action": "auto_execute" | "require_approval" | "escalate",
                "reason": str,
                "risk_level": "low" | "medium" | "high" | "critical",
            }
        """

    def _check_risk_level(self, proposal: FixProposal) -> str:
        """检查风险等级"""

    def _check_fence(self, proposal: FixProposal) -> bool:
        """检查安全围栏"""

    def _check_quota(self) -> bool:
        """检查配额"""
```

## 数据流

### 告警处理流程

```
1. 飞书消息 → LarkClient (WebSocket)
              ↓
2. AlertDetector.is_alert()
              ↓
3. WorkflowRunManager.create_run()
              ↓
4. LangGraph workflow.invoke()
   ├─ ingest: 预处理告警
   ├─ triage: 分类和去重
   ├─ diagnose: LLM 多轮诊断
   │   ├─ 调用诊断插件
   │   └─ 输出诊断结果
   ├─ send_diagnosis_card: 发送卡片
   ├─ await_diagnosis_approval: interrupt
   │   └─ 等待用户点击按钮
   ├─ propose: 生成修复方案
   ├─ policy_evaluate: 安全评估
   ├─ send_proposal_card: 发送卡片
   ├─ await_proposal_approval: interrupt
   │   └─ 等待用户点击按钮
   ├─ execute: 执行修复
   │   └─ 调用修复插件
   ├─ verify: 验证结果
   └─ resolve/escalate: 完成
              ↓
5. 保存结果到 PostgreSQL
              ↓
6. 发送结果通知到飞书
```

### 数据存储

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  incidents  │  │   events    │  │  diagnoses  │     │
│  │  告警记录   │  │  审计时间线 │  │  诊断结果   │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐     │
│  │  proposals  │  │ executions  │  │  knowledge  │     │
│  │  修复方案   │  │  执行记录   │  │  知识库     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              pgvector (向量存储)                 │   │
│  │  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │  embeddings │  │  similarity │               │   │
│  │  │  向量索引   │  │  相似度搜索 │               │   │
│  │  └─────────────┘  └─────────────┘               │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 扩展性设计

### 1. 插件扩展

- 新增插件只需继承 `Plugin` ABC
- 使用 `@register` 装饰器自动注册
- 支持自定义插件目录

### 2. LLM 扩展

- `LLMClient` ABC 统一接口
- 新增 LLM 只需实现 `chat` 和 `complete`
- 通过 `LLM_PROVIDER` 环境变量切换

### 3. 集成扩展

- 模块化设计，各层独立
- 接口清晰，易于替换实现
- 支持自定义告警源

### 4. 存储扩展

- SQLAlchemy ORM 支持多种数据库
- 向量存储可替换（pgvector → Pinecone 等）
- 缓存层可替换（Redis → Memcached 等）

## 性能优化

### 1. 并发处理

- 异步 I/O（asyncio）
- 插件并行执行
- 数据库连接池

### 2. 缓存策略

- Redis 缓存热点数据
- LLM 响应缓存
- 插件结果缓存

### 3. 资源管理

- 数据库连接池管理
- LLM 请求限流
- 插件超时控制

## 安全设计

### 1. 认证授权

- 飞书事件签名验证
- API Key 认证
- RBAC 权限控制

### 2. 数据安全

- 敏感数据加密存储
- 日志脱敏
- 传输加密（HTTPS）

### 3. 操作安全

- 安全围栏机制
- 操作审计日志
- 人工确认流程

## 下一步

- [插件开发](/development/plugin-dev) - 开发自定义插件
- [测试](/development/testing) - 测试策略和工具
- [贡献指南](/development/contributing) - 贡献代码

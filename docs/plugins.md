# 插件系统

ai-fixer 使用插件系统扩展诊断和修复能力。插件分为两类：

- **诊断插件**（diagnostic）：只读操作，LLM 诊断时自动调用
- **修复插件**（remediation）：写操作，可能需要审批

## 内置插件

### Kubernetes 插件

| 插件名 | 类型 | 风险 | 说明 |
|--------|------|------|------|
| `k8s.describe_pod` | diagnostic | low | 获取 Pod 详情 |
| `k8s.list_pods` | diagnostic | low | 列出 Pod |
| `k8s.get_events` | diagnostic | low | 获取 K8s 事件 |
| `k8s.get_pod_logs` | diagnostic | low | 获取 Pod 日志 |
| `k8s.describe_node` | diagnostic | low | 获取 Node 详情 |
| `k8s.top_pods` | diagnostic | low | Pod 资源使用 |
| `k8s.restart_pod` | remediation | medium | 重启 Pod |
| `k8s.scale_deployment` | remediation | medium | 扩缩容 |
| `k8s.rollback_deployment` | remediation | high | 回滚 Deployment |
| `k8s.cordon_node` | remediation | medium | 标记 Node 不可调度 |
| `k8s.delete_evicted_pods` | remediation | low | 清理 Evicted Pod |

### 数据库插件

| 插件名 | 类型 | 风险 | 说明 |
|--------|------|------|------|
| `pg.slow_queries` | diagnostic | low | 慢查询 |
| `pg.lock_waits` | diagnostic | low | 锁等待 |
| `pg.active_connections` | diagnostic | low | 活跃连接 |
| `pg.replication_lag` | diagnostic | low | 复制延迟 |
| `pg.table_bloat` | diagnostic | low | 表膨胀 |
| `pg.kill_deadlock` | remediation | high | 终止死锁 |
| `pg.vacuum_table` | remediation | medium | VACUUM 表 |
| `pg.terminate_query` | remediation | medium | 终止查询 |

### 监控插件

| 插件名 | 类型 | 风险 | 说明 |
|--------|------|------|------|
| `prom.query` | diagnostic | low | Prometheus 即时查询 |
| `prom.query_range` | diagnostic | low | Prometheus 范围查询 |
| `loki.query` | diagnostic | low | Loki 日志查询 |
| `sentry.get_issue` | diagnostic | low | Sentry Issue 详情 |

### 通用插件

| 插件名 | 类型 | 风险 | 说明 |
|--------|------|------|------|
| `shell.exec` | diagnostic | medium | 执行 shell 命令（只读） |
| `shell.exec_write` | remediation | high | 执行 shell 命令（写操作，需审批） |
| `runbook.search` | diagnostic | low | 搜索 Runbook |
| `llm.kubectl_action` | remediation | high | LLM 兜底 kubectl 命令 |

## 插件管理

访问 http://localhost:5173/plugins 管理插件。

### 启用/禁用

- 点击插件行的开关即可启用/禁用
- 状态持久化到数据库，重启后保持
- 禁用的插件不会被 LLM 调用

### 热重载

点击右上角「🔄 热重载」按钮，重新扫描所有插件目录。

适用场景：
- 上传新插件后
- 修改插件代码后
- 删除插件文件后

## 自定义插件

### 创建插件

在 `custom_plugins/` 目录创建 `.py` 文件：

```python
from typing import Any, ClassVar
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class MyPlugin:
    """我的自定义插件。"""

    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "目标"},
        },
        "required": ["target"],
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="custom.my_plugin",        # 必须全局唯一
            category="diagnostic",           # diagnostic | remediation | fallback
            description="插件描述",
            risk_level="low",                # low | medium | high | critical
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        target = args.get("target", "")

        # 实现插件逻辑
        try:
            result = f"处理 {target}"
            return PluginResult(
                ok=True,
                output={"result": result},
                evidence_snippets=[result],
            )
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))
```

### 上传插件

**方式一：文件放置**

将 `.py` 文件放入 `custom_plugins/` 目录，然后在前端点击「🔄 热重载」。

**方式二：Web 上传**

在 http://localhost:5173/plugins 点击「📤 上传插件」，选择 `.py` 文件。

### 插件规范

| 要求 | 说明 |
|------|------|
| 文件格式 | `.py`，UTF-8 编码 |
| 命名规则 | `name` 必须全局唯一，建议 `custom.` 前缀 |
| 注册方式 | 使用 `@register(global_registry)` 装饰器 |
| 返回值 | 必须返回 `PluginResult` |
| 超时 | `timeout_seconds` 最大 120 秒 |
| 安全 | 禁止 `os.system`、`subprocess.call`、`exec()` 等 |

### 删除插件

在前端插件列表中，自定义插件有「删除」按钮。点击后确认即可删除。

## 插件与 LLM 的关系

### 两阶段诊断

1. **第一阶段**：LLM 不使用工具，仅根据告警文本和环境上下文分析
2. **第二阶段**：如果置信度 < 阈值（默认 0.7），LLM 调用相关插件深入排查

### 工具选择

LLM 不会看到所有插件。系统根据告警类别自动选择相关工具：

| 告警类别 | 提供的工具 |
|----------|-----------|
| K8s 相关 | shell.exec + k8s.* |
| 数据库相关 | shell.exec + pg.* |
| 监控相关 | shell.exec + prom.* |
| 日志相关 | shell.exec + loki.* |
| 其他 | shell.exec + k8s.list_pods + prom.query |

最多提供 6 个工具，避免 LLM 困惑。

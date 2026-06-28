# 插件系统

了解和开发 ai-fixer 的插件系统。

## 插件概述

ai-fixer 使用插件系统扩展诊断和修复能力。插件分为两类：

- **诊断插件（Diagnostic）**：只读操作，用于收集信息
- **修复插件（Remediation）**：写操作，会修改系统状态

## 内置插件

### Kubernetes 插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `list_pods` | diagnostic | 列出 Pod |
| `describe_pod` | diagnostic | 查看 Pod 详情 |
| `get_pod_logs` | diagnostic | 获取 Pod 日志 |
| `get_events` | diagnostic | 获取 K8s 事件 |
| `top_pods` | diagnostic | 查看 Pod 资源使用 |
| `restart_pod` | remediation | 重启 Pod |
| `scale_deployment` | remediation | 扩缩容 |
| `rollback_deployment` | remediation | 回滚部署 |
| `cordon_node` | remediation | 节点维护 |
| `delete_evicted_pods` | remediation | 清理驱逐 Pod |

### 数据库插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `slow_queries` | diagnostic | 查询慢查询 |
| `lock_waits` | diagnostic | 查询锁等待 |
| `active_connections` | diagnostic | 查询活跃连接 |
| `replication_lag` | diagnostic | 查询复制延迟 |
| `table_bloat` | diagnostic | 查询表膨胀 |
| `kill_deadlock` | remediation | 终止死锁进程 |
| `vacuum_table` | remediation | 清理表 |
| `terminate_query` | remediation | 终止查询 |

### 监控插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `prom.query` | diagnostic | Prometheus 即时查询 |
| `prom.query_range` | diagnostic | Prometheus 范围查询 |
| `loki.query` | diagnostic | Loki 日志查询 |
| `sentry.get_issue` | diagnostic | Sentry 问题查询 |

### 其他插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `shell.exec` | diagnostic | 执行 Shell 命令（只读） |
| `shell.exec_write` | remediation | 执行 Shell 命令（写操作） |
| `runbook.search` | diagnostic | 搜索 Runbook |
| `llm.kubectl_action` | diagnostic | LLM 生成 kubectl 命令 |

## 插件开发

### 1. 创建插件文件

在 `app/plugins/builtin/` 或 `custom_plugins/` 目录下创建新文件：

```python
# app/plugins/builtin/my_plugin.py

from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class MyPlugin(Plugin):
    """我的自定义插件"""

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="my_plugin",
            description="查询自定义服务状态",
            category="diagnostic",  # 或 "remediation"
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "服务名称",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "命名空间",
                        "default": "default",
                    },
                },
                "required": ["service_name"],
            },
        )

    async def execute(self, service_name: str, namespace: str = "default") -> dict:
        """
        执行插件逻辑

        Args:
            service_name: 服务名称
            namespace: 命名空间

        Returns:
            dict: 执行结果
        """
        # 在这里实现你的逻辑
        # 例如：查询服务状态、调用 API 等

        return {
            "status": "running",
            "replicas": 3,
            "ready_replicas": 3,
            "message": f"Service {service_name} in {namespace} is healthy",
        }
```

### 2. 插件规范

#### PluginSpec 字段

```python
PluginSpec(
    name="plugin_name",           # 插件名称（唯一）
    description="插件描述",        # 简短描述
    category="diagnostic",        # 类型：diagnostic 或 remediation
    parameters={                  # JSON Schema 定义参数
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "参数说明",
            },
        },
        "required": ["param1"],
    },
)
```

#### execute 方法

```python
async def execute(self, **kwargs) -> dict:
    """
    执行插件逻辑

    Args:
        **kwargs: 根据 parameters 定义的参数

    Returns:
        dict: 执行结果，建议包含以下字段：
            - success: bool - 是否成功
            - data: Any - 返回数据
            - message: str - 结果描述
            - error: str - 错误信息（如果失败）
    """
    try:
        # 执行逻辑
        result = await some_operation()
        return {
            "success": True,
            "data": result,
            "message": "操作成功",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"操作失败: {e}",
        }
```

### 3. 使用装饰器注册

```python
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class MyPlugin(Plugin):
    # ...
```

### 4. 测试插件

```python
import pytest
from app.plugins.registry import global_registry

def test_my_plugin():
    # 获取插件
    plugin = global_registry.get("my_plugin")
    assert plugin is not None

    # 测试执行
    result = await plugin.execute(
        service_name="user-service",
        namespace="production"
    )
    assert result["success"] is True
```

## 自定义插件目录

将自定义插件放入 `custom_plugins/` 目录即可自动加载：

```
ai-fixer/
├── app/
│   └── plugins/
│       └── builtin/      # 内置插件
├── custom_plugins/        # 自定义插件（自动加载）
│   ├── __init__.py
│   ├── my_plugin1.py
│   └── my_plugin2.py
```

### 命名建议

自定义插件建议使用 `custom.` 前缀：

```python
@register(global_registry)
class CustomMyPlugin(Plugin):
    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="custom.my_plugin",
            # ...
        )
```

## 插件最佳实践

### 1. 错误处理

```python
async def execute(self, **kwargs) -> dict:
    try:
        # 验证参数
        if not kwargs.get("service_name"):
            return {
                "success": False,
                "error": "Missing required parameter: service_name",
            }

        # 执行逻辑
        result = await self._do_something(kwargs)
        return {"success": True, "data": result}

    except ConnectionError as e:
        return {
            "success": False,
            "error": f"Connection failed: {e}",
            "retry": True,  # 可重试
        }
    except Exception as e:
        logger.exception("Plugin execution failed")
        return {
            "success": False,
            "error": str(e),
        }
```

### 2. 超时控制

```python
import asyncio

async def execute(self, **kwargs) -> dict:
    try:
        result = await asyncio.wait_for(
            self._long_running_operation(),
            timeout=30.0
        )
        return {"success": True, "data": result}
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Operation timed out",
        }
```

### 3. 日志记录

```python
import structlog

logger = structlog.get_logger()

async def execute(self, **kwargs) -> dict:
    logger.info("plugin.execute.start", plugin="my_plugin", **kwargs)

    try:
        result = await self._do_something(kwargs)
        logger.info("plugin.execute.success", plugin="my_plugin", result=result)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("plugin.execute.failed", plugin="my_plugin", error=str(e))
        return {"success": False, "error": str(e)}
```

### 4. 资源清理

```python
async def execute(self, **kwargs) -> dict:
    client = None
    try:
        client = await create_client()
        result = await client.fetch_data()
        return {"success": True, "data": result}
    finally:
        if client:
            await client.close()
```

## 插件配置

部分插件支持通过配置调整行为：

### 环境变量配置

```python
import os

async def execute(self, **kwargs) -> dict:
    api_url = os.getenv("MY_PLUGIN_API_URL", "http://default-url")
    api_key = os.getenv("MY_PLUGIN_API_KEY")

    if not api_key:
        return {"success": False, "error": "API key not configured"}

    # ...
```

### 动态配置

```python
from app.config.dynamic import DynamicConfig

async def execute(self, **kwargs) -> dict:
    config = DynamicConfig()
    timeout = await config.get("my_plugin.timeout", default=30)

    # ...
```

## 故障排查

### 插件未加载

```bash
# 检查插件是否注册
curl http://localhost:8080/api/plugins | jq '.[] | select(.name == "my_plugin")'

# 查看日志
docker-compose logs app | grep -i "plugin"
```

### 插件执行失败

```bash
# 查看 Incident 详情
curl http://localhost:8080/api/incidents/{id} | jq '.events[] | select(.type == "tool_call")'
```

## 下一步

- [架构设计](/development/architecture) - 了解插件在架构中的位置
- [贡献指南](/development/contributing) - 贡献新插件
- [API 文档](/api/) - 插件 API 接口

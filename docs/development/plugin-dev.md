# 插件开发

深入了解如何开发自定义插件。

## 插件架构

```
┌─────────────────────────────────────────────────────────┐
│                    插件系统架构                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Plugin    │    │ PluginSpec  │    │  Registry   │ │
│  │    ABC      │◄───│   规格定义  │───►│   注册表    │ │
│  └──────┬──────┘    └─────────────┘    └──────┬──────┘ │
│         │                                      │        │
│         ▼                                      ▼        │
│  ┌─────────────┐                      ┌─────────────┐  │
│  │  execute()  │                      │  discover() │  │
│  │  执行逻辑   │                      │  自动发现   │  │
│  └─────────────┘                      └─────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              内置插件 (builtin/)                 │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │
│  │  │  K8s    │  │Database │  │Monitor  │         │   │
│  │  └─────────┘  └─────────┘  └─────────┘         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │            自定义插件 (custom_plugins/)          │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │
│  │  │custom.1 │  │custom.2 │  │custom.3 │         │   │
│  │  └─────────┘  └─────────┘  └─────────┘         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 开发流程

### 1. 确定插件类型

- **诊断插件（diagnostic）**：只读操作，收集信息
- **修复插件（remediation）**：写操作，修改系统状态

### 2. 创建插件文件

```python
# app/plugins/builtin/my_plugin.py
# 或 custom_plugins/my_plugin.py
```

### 3. 实现插件类

```python
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class MyPlugin(Plugin):
    """我的自定义插件"""

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="my_plugin",
            description="插件描述",
            category="diagnostic",
            parameters={
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

    async def execute(self, param1: str) -> dict:
        """
        执行插件逻辑

        Args:
            param1: 参数说明

        Returns:
            dict: 执行结果
        """
        try:
            # 实现逻辑
            result = await self._do_something(param1)
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

### 4. 添加测试

```python
# tests/plugins/test_my_plugin.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_plugin():
    plugin = MyPlugin()
    result = await plugin.execute(param1="test")

    assert result["success"] is True
    assert "data" in result
```

## 完整示例

### 示例 1: 查询服务状态插件

```python
# app/plugins/builtin/service_status.py

import httpx
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class ServiceStatusPlugin(Plugin):
    """查询服务健康状态"""

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="service_status",
            description="查询服务健康状态",
            category="diagnostic",
            parameters={
                "type": "object",
                "properties": {
                    "service_url": {
                        "type": "string",
                        "description": "服务健康检查 URL",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒）",
                        "default": 5,
                    },
                },
                "required": ["service_url"],
            },
        )

    async def execute(
        self,
        service_url: str,
        timeout: int = 5,
    ) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    service_url,
                    timeout=timeout,
                )

            return {
                "success": True,
                "data": {
                    "status_code": response.status_code,
                    "healthy": response.status_code == 200,
                    "response_time": response.elapsed.total_seconds(),
                },
                "message": f"服务状态: {'健康' if response.status_code == 200 else '异常'}",
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "请求超时",
                "message": f"服务 {service_url} 响应超时",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"查询失败: {e}",
            }
```

### 示例 2: 重启 Deployment 插件

```python
# app/plugins/builtin/advanced_restart.py

from kubernetes_asyncio import client, config
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class AdvancedRestartPlugin(Plugin):
    """高级重启 Deployment（支持滚动更新策略）"""

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="advanced_restart",
            description="高级重启 Deployment",
            category="remediation",
            parameters={
                "type": "object",
                "properties": {
                    "deployment": {
                        "type": "string",
                        "description": "Deployment 名称",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "命名空间",
                        "default": "default",
                    },
                    "strategy": {
                        "type": "string",
                        "description": "重启策略",
                        "enum": ["rolling", "recreate"],
                        "default": "rolling",
                    },
                },
                "required": ["deployment"],
            },
        )

    async def execute(
        self,
        deployment: str,
        namespace: str = "default",
        strategy: str = "rolling",
    ) -> dict:
        try:
            # 加载 K8s 配置
            await config.load_kube_config()
            apps_v1 = client.AppsV1Api()

            # 获取当前 Deployment
            deploy = await apps_v1.read_namespaced_deployment(
                name=deployment,
                namespace=namespace,
            )

            # 更新注解触发重启
            if not deploy.spec.template.metadata.annotations:
                deploy.spec.template.metadata.annotations = {}

            deploy.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = (
                datetime.now().isoformat()
            )

            # 执行更新
            await apps_v1.patch_namespaced_deployment(
                name=deployment,
                namespace=namespace,
                body=deploy,
            )

            return {
                "success": True,
                "data": {
                    "deployment": deployment,
                    "namespace": namespace,
                    "strategy": strategy,
                },
                "message": f"Deployment {deployment} 重启成功",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"重启失败: {e}",
            }
```

### 示例 3: 查询外部 API 插件

```python
# app/plugins/builtin/external_api.py

import os
import httpx
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class ExternalAPIPlugin(Plugin):
    """查询外部 API"""

    def __init__(self):
        self.api_key = os.getenv("EXTERNAL_API_KEY")
        self.base_url = os.getenv("EXTERNAL_API_URL", "https://api.example.com")

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="external_api",
            description="查询外部 API",
            category="diagnostic",
            parameters={
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "API 端点",
                    },
                    "params": {
                        "type": "object",
                        "description": "查询参数",
                        "additionalProperties": True,
                    },
                },
                "required": ["endpoint"],
            },
        )

    async def execute(
        self,
        endpoint: str,
        params: dict = None,
    ) -> dict:
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not configured",
                "message": "请配置 EXTERNAL_API_KEY 环境变量",
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{endpoint}",
                    params=params or {},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30,
                )

            return {
                "success": True,
                "data": response.json(),
                "message": "查询成功",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"查询失败: {e}",
            }
```

## 高级特性

### 1. 插件配置

从环境变量或配置文件读取：

```python
import os
from app.config.dynamic import DynamicConfig

class ConfigurablePlugin(Plugin):
    def __init__(self):
        self.config = DynamicConfig()

    async def execute(self, **kwargs) -> dict:
        # 从环境变量读取
        api_key = os.getenv("MY_PLUGIN_API_KEY")

        # 从动态配置读取
        timeout = await self.config.get(
            "my_plugin.timeout",
            default=30,
        )

        # ...
```

### 2. 依赖注入

使用依赖注入管理插件依赖：

```python
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry
from app.k8s.client import K8sClient

@register(global_registry)
class K8sPlugin(Plugin):
    def __init__(self, k8s_client: K8sClient = None):
        self.k8s_client = k8s_client or K8sClient()

    @property
    def spec(self) -> PluginSpec:
        # ...

    async def execute(self, **kwargs) -> dict:
        pods = await self.k8s_client.list_pods(**kwargs)
        return {"success": True, "data": pods}
```

### 3. 并发执行

插件内部并发执行多个操作：

```python
import asyncio

async def execute(self, **kwargs) -> dict:
    # 并发执行多个查询
    results = await asyncio.gather(
        self._check_service_a(),
        self._check_service_b(),
        self._check_service_c(),
        return_exceptions=True,
    )

    # 处理结果
    services = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            services[f"service_{i}"] = {"error": str(result)}
        else:
            services[f"service_{i}"] = result

    return {
        "success": True,
        "data": services,
    }
```

### 4. 资源管理

正确管理资源（连接、文件等）：

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

### 5. 重试逻辑

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryPlugin(Plugin):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _fetch_with_retry(self, url: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

    async def execute(self, url: str) -> dict:
        try:
            data = await self._fetch_with_retry(url)
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

## 测试插件

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_plugin_success():
    plugin = MyPlugin()

    # Mock 依赖
    with patch("app.external.api_call", new_callable=AsyncMock) as mock:
        mock.return_value = {"result": "ok"}
        result = await plugin.execute(param1="test")

    assert result["success"] is True
    assert result["data"]["result"] == "ok"

@pytest.mark.asyncio
async def test_plugin_failure():
    plugin = MyPlugin()

    # Mock 失败场景
    with patch("app.external.api_call", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("Connection failed")
        result = await plugin.execute(param1="test")

    assert result["success"] is False
    assert "Connection failed" in result["error"]
```

### 集成测试

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_plugin_with_real_service():
    plugin = ServiceStatusPlugin()
    result = await plugin.execute(
        service_url="http://localhost:8080/health"
    )

    assert result["success"] is True
    assert result["data"]["healthy"] is True
```

## 最佳实践

### 1. 单一职责

每个插件只做一件事：

```python
# 好：职责清晰
class ListPodsPlugin(Plugin):
    async def execute(self, **kwargs) -> dict:
        return await list_pods(**kwargs)

class DescribePodPlugin(Plugin):
    async def execute(self, **kwargs) -> dict:
        return await describe_pod(**kwargs)

# 不好：职责混乱
class K8sPlugin(Plugin):
    async def execute(self, action: str, **kwargs) -> dict:
        if action == "list":
            return await list_pods(**kwargs)
        elif action == "describe":
            return await describe_pod(**kwargs)
        # ...
```

### 2. 参数验证

```python
async def execute(self, **kwargs) -> dict:
    # 验证必需参数
    if "service_name" not in kwargs:
        return {
            "success": False,
            "error": "Missing required parameter: service_name",
        }

    # 验证参数类型
    service_name = kwargs["service_name"]
    if not isinstance(service_name, str):
        return {
            "success": False,
            "error": "service_name must be a string",
        }

    # 验证参数范围
    if len(service_name) > 100:
        return {
            "success": False,
            "error": "service_name too long (max 100 chars)",
        }

    # ...
```

### 3. 错误处理

```python
async def execute(self, **kwargs) -> dict:
    try:
        result = await self._do_operation(kwargs)
        return {
            "success": True,
            "data": result,
            "message": "操作成功",
        }
    except ValueError as e:
        # 参数错误
        return {
            "success": False,
            "error": f"Invalid parameter: {e}",
            "message": "参数错误",
        }
    except ConnectionError as e:
        # 连接错误（可重试）
        return {
            "success": False,
            "error": f"Connection failed: {e}",
            "message": "连接失败，请稍后重试",
            "retry": True,
        }
    except Exception as e:
        # 未知错误
        logger.exception("Plugin execution failed")
        return {
            "success": False,
            "error": str(e),
            "message": "内部错误",
        }
```

### 4. 日志记录

```python
import structlog

logger = structlog.get_logger()

async def execute(self, **kwargs) -> dict:
    logger.info(
        "plugin.execute.start",
        plugin=self.spec.name,
        params=kwargs,
    )

    try:
        result = await self._do_operation(kwargs)
        logger.info(
            "plugin.execute.success",
            plugin=self.spec.name,
            result=result,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(
            "plugin.execute.failed",
            plugin=self.spec.name,
            error=str(e),
        )
        return {"success": False, "error": str(e)}
```

## 下一步

- [插件系统](/guide/plugins) - 了解插件系统
- [架构设计](/development/architecture) - 插件在架构中的位置
- [贡献指南](/development/contributing) - 贡献插件到项目

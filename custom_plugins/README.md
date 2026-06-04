# 自定义插件目录

将自定义插件 `.py` 文件放在此目录中，系统会自动加载。

## 插件模板

```python
from typing import Any, ClassVar
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class MyCustomPlugin:
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"},
        },
        "required": ["param1"],
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="custom.my_plugin",           # 必须唯一
            category="diagnostic",              # diagnostic | remediation | fallback
            description="插件描述",
            risk_level="low",                   # low | medium | high | critical
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        # 实现插件逻辑
        return PluginResult(ok=True, output={"result": "..."})
```

## 注意事项

- 插件文件名必须以 `.py` 结尾
- 插件类必须用 `@register(global_registry)` 装饰
- `name` 必须全局唯一，建议用 `custom.` 前缀
- 上传时会进行基本安全检查，禁止 `os.system`、`subprocess.call` 等危险调用

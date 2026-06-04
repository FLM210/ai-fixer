from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sDescribeNode(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "node_name": {"type": "string", "minLength": 1},
        },
        "required": ["node_name"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.describe_node",
            category="diagnostic",
            description="获取 node 详情",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        try:
            data = await self._client.describe_node(args["node_name"])
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"describe_node failed: {e}")

        return PluginResult(ok=True, output=data)

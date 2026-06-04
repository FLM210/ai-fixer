from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sCordonNode(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "node_name": {"type": "string", "minLength": 1},
            "reason": {"type": "string"},
        },
        "required": ["node_name", "reason"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.cordon_node",
            category="remediation",
            description="标记 node 为不可调度( cordon )。适用于 node 异常需要隔离的场景。",
            risk_level="medium",
            timeout_seconds=15,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})
        try:
            result = await self._client.cordon_node(args["node_name"])
            return PluginResult(ok=True, output={"cordoned": True, "detail": result})
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

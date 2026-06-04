from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sTopPods(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "sort_by": {"type": "string", "enum": ["cpu", "memory"], "default": "cpu"},
        },
        "required": ["namespace"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.top_pods",
            category="diagnostic",
            description="pod 资源使用排行",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        try:
            pods = await self._client.top_pods(
                args["namespace"],
                sort_by=args.get("sort_by", "cpu"),
            )
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"top_pods failed: {e}")

        return PluginResult(ok=True, output={"pods": pods})

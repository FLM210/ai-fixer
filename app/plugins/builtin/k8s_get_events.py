from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sGetEvents(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "field_selector": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["namespace"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.get_events",
            category="diagnostic",
            description="获取 K8s 事件",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        try:
            events = await self._client.get_events(
                args["namespace"],
                field_selector=args.get("field_selector"),
                limit=args.get("limit", 50),
            )
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"get_events failed: {e}")

        return PluginResult(ok=True, output={"events": events})

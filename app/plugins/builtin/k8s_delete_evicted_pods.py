from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sDeleteEvictedPods(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
        },
        "required": ["namespace"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.delete_evicted_pods",
            category="remediation",
            description="清理 namespace 下 Evicted/Completed 状态的 pod,释放资源。",
            risk_level="low",
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})
        try:
            result = await self._client.delete_evicted_pods(args["namespace"])
            return PluginResult(ok=True, output={"deleted_count": result.get("deleted_count", 0)})
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

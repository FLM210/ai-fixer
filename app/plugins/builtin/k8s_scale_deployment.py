from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sScaleDeployment(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "deployment": {"type": "string", "minLength": 1},
            "replicas": {"type": "integer", "minimum": 0, "maximum": 100},
        },
        "required": ["namespace", "deployment", "replicas"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.scale_deployment",
            category="remediation",
            description="扩缩容 deployment 副本数。适用于负载不均或需要快速扩容的场景。",
            risk_level="medium",
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})
        try:
            result = await self._client.scale_deployment(
                args["namespace"], args["deployment"], args["replicas"]
            )
            return PluginResult(ok=True, output={"replicas": result.get("replicas")})
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

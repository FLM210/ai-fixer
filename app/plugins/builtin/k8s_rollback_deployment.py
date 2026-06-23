from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sRollbackDeployment(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "deployment": {"type": "string", "minLength": 1},
            "revision": {
                "type": "integer",
                "description": "回滚到指定 revision,不指定则回滚到上一个",
            },
        },
        "required": ["namespace", "deployment"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.rollback_deployment",
            category="remediation",
            description="回滚 deployment 到上一个 revision。适用于新版本引入问题需要快速回退。",
            risk_level="high",
            timeout_seconds=60,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})
        try:
            result = await self._client.rollback_deployment(
                args["namespace"], args["deployment"], revision=args.get("revision")
            )
            return PluginResult(ok=True, output={"revision": result.get("revision")})
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

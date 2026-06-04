from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sRestartPod(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "pod_name": {"type": "string", "minLength": 1},
            "reason": {"type": "string"},
        },
        "required": ["namespace", "pod_name", "reason"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.restart_pod",
            category="remediation",
            description="删除 pod 触发控制器重建。适用于 pod 无响应但控制器正常的情况。",
            risk_level="medium",
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})
        try:
            result = await self._client.delete_pod(args["namespace"], args["pod_name"])
            return PluginResult(ok=True, output={"deleted": True, "detail": result})
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sGetPodLogs(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "pod": {"type": "string", "minLength": 1},
            "container": {"type": "string"},
            "tail_lines": {"type": "integer", "default": 200},
        },
        "required": ["namespace", "pod"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.get_pod_logs",
            category="diagnostic",
            description="获取指定 pod 容器的日志",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        try:
            logs = await self._client.get_pod_logs(
                args["namespace"],
                args["pod"],
                container=args.get("container"),
                tail_lines=args.get("tail_lines", 200),
            )
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"get_pod_logs failed: {e}")

        return PluginResult(ok=True, output={"logs": logs})

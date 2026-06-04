from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register


@register(global_registry)
class K8sDescribePod(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "minLength": 1},
            "pod": {"type": "string", "minLength": 1},
        },
        "required": ["namespace", "pod"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        # Phase 1 默认用 FakeK8sClient,Phase 2 通过 DI 注入真实实现
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="k8s.describe_pod",
            category="diagnostic",
            description="描述指定 namespace 下某 pod 的状态、容器、最近事件",
            risk_level="low",
            timeout_seconds=10,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        try:
            data = await self._client.describe_pod(args["namespace"], args["pod"])
        except Exception as e:
            return PluginResult(ok=False, output={}, error=f"describe_pod failed: {e}")

        evidence = [f"phase={data.get('phase')}"]
        for ev in data.get("events", []):
            evidence.append(f"event[{ev.get('reason')}]: {ev.get('message')}")
        return PluginResult(ok=True, output=data, evidence_snippets=evidence)

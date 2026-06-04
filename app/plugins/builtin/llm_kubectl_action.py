import shlex
from typing import Any, ClassVar

from app.k8s import FakeK8sClient, K8sClient
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register

# 白名单 verb: 只允许读操作 + 少量安全写操作
ALLOWED_VERBS: set[str] = {"get", "describe", "logs", "top", "delete", "scale", "rollout", "cordon"}

# 黑名单: 禁止危险操作
BLOCKED_VERBS: set[str] = {"apply", "create", "edit", "exec", "cp", "port-forward", "patch", "replace"}


def _extract_verb(command: str) -> str | None:
    """从 kubectl 命令中提取动词。"""
    parts = shlex.split(command)
    for part in parts:
        if part == "kubectl":
            continue
        if part.startswith("-"):
            continue
        return part
    return None


@register(global_registry)
class LLMKubectlAction(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "minLength": 1, "description": "kubectl 命令(不含 kubectl 前缀也可)"},
            "reason": {"type": "string", "description": "执行原因"},
        },
        "required": ["command", "reason"],
        "additionalProperties": False,
    }

    def __init__(self, k8s_client: K8sClient | None = None) -> None:
        self._client = k8s_client or FakeK8sClient()

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="llm.kubectl_action",
            category="remediation",
            description="LLM 兜底: 执行 kubectl 命令(白名单 verb)。当插件库无法匹配时使用, 强制提升 risk_level。",
            risk_level="high",
            timeout_seconds=30,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        if ctx.dry_run:
            return PluginResult(ok=True, output={"dry_run": True})

        command = args["command"]
        verb = _extract_verb(command)

        if verb is None:
            return PluginResult(ok=False, output={}, error="无法解析 kubectl 命令")

        if verb in BLOCKED_VERBS:
            return PluginResult(ok=False, output={}, error=f"拒绝执行: verb \"{verb}\" 在黑名单中")

        if verb not in ALLOWED_VERBS:
            return PluginResult(ok=False, output={}, error=f"拒绝执行: verb \"{verb}\" 不在白名单中")

        try:
            result = await self._client.exec_kubectl(command)
            exit_code = result.get("exit_code", -1)
            return PluginResult(
                ok=exit_code == 0,
                output={
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exit_code": exit_code,
                },
                error=result.get("stderr") if exit_code != 0 else None,
            )
        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))

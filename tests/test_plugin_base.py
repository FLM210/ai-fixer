from typing import Any

import pytest

from app.plugins.base import (
    Plugin,
    PluginCategory,
    PluginContext,
    PluginResult,
    PluginSpec,
)


def _spec(name: str = "k8s.describe_pod", category: PluginCategory = "diagnostic") -> PluginSpec:
    return PluginSpec(
        name=name,
        category=category,
        description="describe a pod",
        risk_level="low",
        timeout_seconds=10,
        input_schema={
            "type": "object",
            "properties": {"pod": {"type": "string"}, "namespace": {"type": "string"}},
            "required": ["pod", "namespace"],
            "additionalProperties": False,
        },
    )


class _DummyPlugin(Plugin):
    @property
    def spec(self) -> PluginSpec:
        return _spec()

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        return PluginResult(
            ok=True,
            output={"pod": args["pod"]},
            evidence_snippets=[f"described {args['pod']}"],
        )


@pytest.mark.asyncio
async def test_plugin_executes() -> None:
    plugin = _DummyPlugin()
    ctx = PluginContext(incident_id="inc-1", actor="agent", trace_id="t-1", dry_run=False)
    result = await plugin.execute(ctx, {"pod": "p1", "namespace": "n1"})
    assert result.ok is True
    assert result.output == {"pod": "p1"}


def test_plugin_validates_args_ok() -> None:
    plugin = _DummyPlugin()
    plugin.validate_args({"pod": "p", "namespace": "n"})


def test_plugin_validates_args_rejects_missing() -> None:
    plugin = _DummyPlugin()
    with pytest.raises(ValueError):
        plugin.validate_args({"pod": "p"})


def test_plugin_validates_args_rejects_extra() -> None:
    plugin = _DummyPlugin()
    with pytest.raises(ValueError):
        plugin.validate_args({"pod": "p", "namespace": "n", "x": 1})


def test_plugin_spec_categories() -> None:
    diag = _spec(category="diagnostic")
    rem = _spec(name="k8s.restart_pod", category="remediation")
    assert diag.category == "diagnostic"
    assert rem.category == "remediation"


def test_plugin_result_failure_carries_error() -> None:
    res = PluginResult(ok=False, output={}, error="boom")
    assert res.ok is False
    assert res.error == "boom"

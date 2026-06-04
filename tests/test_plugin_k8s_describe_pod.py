import pytest

from app.k8s import FakeK8sClient
from app.plugins.base import PluginContext
from app.plugins.builtin.k8s_describe_pod import K8sDescribePod


@pytest.mark.asyncio
async def test_describe_pod_success() -> None:
    fake = FakeK8sClient(describe_pod_payload={
        "phase": "CrashLoopBackOff",
        "containers": [{"name": "app", "ready": False, "restartCount": 5}],
        "events": [{"reason": "BackOff", "message": "Back-off restarting failed container"}],
    })
    plugin = K8sDescribePod(k8s_client=fake)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1")

    plugin.validate_args({"namespace": "prod", "pod": "app-xyz"})
    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "app-xyz"})

    assert result.ok is True
    assert result.output["phase"] == "CrashLoopBackOff"
    assert any("BackOff" in e for e in result.evidence_snippets)
    assert fake.calls == [{"action": "describe_pod", "namespace": "prod", "name": "app-xyz"}]


def test_describe_pod_spec_metadata() -> None:
    plugin = K8sDescribePod(k8s_client=FakeK8sClient())
    spec = plugin.spec
    assert spec.name == "k8s.describe_pod"
    assert spec.category == "diagnostic"
    assert spec.risk_level == "low"
    assert "namespace" in spec.input_schema["required"]
    assert "pod" in spec.input_schema["required"]


def test_describe_pod_rejects_invalid_args() -> None:
    plugin = K8sDescribePod(k8s_client=FakeK8sClient())
    with pytest.raises(ValueError):
        plugin.validate_args({"pod": "p"})  # missing namespace
    with pytest.raises(ValueError):
        plugin.validate_args({"pod": "p", "namespace": "n", "extra": 1})


@pytest.mark.asyncio
async def test_describe_pod_dry_run_does_not_call_client() -> None:
    fake = FakeK8sClient()
    plugin = K8sDescribePod(k8s_client=fake)
    ctx = PluginContext(incident_id="i-1", actor="agent", trace_id="t-1", dry_run=True)
    result = await plugin.execute(ctx, {"namespace": "prod", "pod": "p"})
    assert result.ok is True
    assert result.output == {"dry_run": True}
    assert fake.calls == []


def test_plugin_registered_in_global_registry_after_discover() -> None:
    from app.plugins import global_registry
    global_registry.clear()
    global_registry.discover_builtin()
    assert global_registry.has("k8s.describe_pod")
    global_registry.clear()

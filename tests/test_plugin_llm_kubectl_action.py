from unittest.mock import AsyncMock

import pytest

from app.plugins.base import PluginContext
from app.plugins.builtin.llm_kubectl_action import LLMKubectlAction


@pytest.fixture
def ctx() -> PluginContext:
    return PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1")


@pytest.mark.asyncio
async def test_kubectl_action_whitelisted_verb(ctx: PluginContext) -> None:
    mock_k8s = AsyncMock()
    mock_k8s.exec_kubectl.return_value = {
        "stdout": "pod/app-1 deleted",
        "stderr": "",
        "exit_code": 0,
    }
    plugin = LLMKubectlAction(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx,
        {
            "command": "kubectl delete pod app-1 -n prod",
            "reason": "unresponsive",
        },
    )
    assert result.ok is True
    assert result.output["exit_code"] == 0


@pytest.mark.asyncio
async def test_kubectl_action_blacklisted_verb(ctx: PluginContext) -> None:
    plugin = LLMKubectlAction()
    result = await plugin.execute(
        ctx,
        {
            "command": "kubectl exec -it app-1 -- /bin/sh",
            "reason": "debug",
        },
    )
    assert result.ok is False
    assert "黑名单" in result.error


@pytest.mark.asyncio
async def test_kubectl_action_dry_run(ctx: PluginContext) -> None:
    ctx_dry = PluginContext(incident_id="inc-1", actor="user1", trace_id="trace-1", dry_run=True)
    plugin = LLMKubectlAction()
    result = await plugin.execute(
        ctx_dry, {"command": "kubectl get pods -n prod", "reason": "test"}
    )
    assert result.output == {"dry_run": True}


@pytest.mark.asyncio
async def test_kubectl_action_unlisted_verb(ctx: PluginContext) -> None:
    """verb 不在白名单也不在黑名单时应拒绝。"""
    plugin = LLMKubectlAction()
    result = await plugin.execute(
        ctx,
        {
            "command": "kubectl annotate pod app-1 key=value -n prod",
            "reason": "test",
        },
    )
    assert result.ok is False
    assert "不在白名单" in result.error


@pytest.mark.asyncio
async def test_kubectl_action_parse_error(ctx: PluginContext) -> None:
    """空命令应返回解析错误。"""
    plugin = LLMKubectlAction()
    result = await plugin.execute(
        ctx,
        {
            "command": "",
            "reason": "test",
        },
    )
    assert result.ok is False


@pytest.mark.asyncio
async def test_kubectl_action_kubectl_prefix_optional(ctx: PluginContext) -> None:
    """不带 kubectl 前缀的命令也能正确解析。"""
    mock_k8s = AsyncMock()
    mock_k8s.exec_kubectl.return_value = {"stdout": "ok", "stderr": "", "exit_code": 0}
    plugin = LLMKubectlAction(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx,
        {
            "command": "get pods -n prod",
            "reason": "check",
        },
    )
    assert result.ok is True
    mock_k8s.exec_kubectl.assert_awaited_once_with("get pods -n prod")


@pytest.mark.asyncio
async def test_kubectl_action_client_exception(ctx: PluginContext) -> None:
    """client 抛异常时应捕获并返回错误。"""
    mock_k8s = AsyncMock()
    mock_k8s.exec_kubectl.side_effect = RuntimeError("connection refused")
    plugin = LLMKubectlAction(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx,
        {
            "command": "kubectl get pods -n prod",
            "reason": "test",
        },
    )
    assert result.ok is False
    assert "connection refused" in result.error


@pytest.mark.asyncio
async def test_kubectl_action_nonzero_exit(ctx: PluginContext) -> None:
    """exit_code 非零时 ok=False。"""
    mock_k8s = AsyncMock()
    mock_k8s.exec_kubectl.return_value = {
        "stdout": "",
        "stderr": "Error from server: NotFound",
        "exit_code": 1,
    }
    plugin = LLMKubectlAction(k8s_client=mock_k8s)
    result = await plugin.execute(
        ctx,
        {
            "command": "kubectl get pod missing -n prod",
            "reason": "test",
        },
    )
    assert result.ok is False
    assert result.output["exit_code"] == 1
    assert result.error == "Error from server: NotFound"

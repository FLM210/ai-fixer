from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.diagnose import diagnose_node, run_diagnose_loop
from app.graph.state import GraphState


def _make_state(**overrides: object) -> GraphState:
    base: GraphState = {
        "incident_id": "inc-1",
        "trace_id": "trace-1",
        "raw_alert": "[告警] P1 order-api pod crashloop",
        "source_meta": {"chat_id": "oc_test", "msg_id": "om_test", "sender": "user1", "ts": 123},
        "category": "k8s_pod_crash",
        "severity": "p1",
        "service": "order-api",
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": None,
        "confidence": None,
        "proposals": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "execution_results": [],
        "final_status": None,
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


@pytest.mark.asyncio
async def test_diagnose_produces_summary() -> None:
    state = _make_state()
    with patch("app.graph.nodes.diagnose.run_diagnose_loop", new_callable=AsyncMock) as mock_loop:
        mock_loop.return_value = {
            "diagnosis_summary": "Pod OOMKilled, memory limit too low",
            "confidence": 0.85,
            "evidence": {"k8s.describe_pod": [{"phase": "CrashLoopBackOff"}]},
            "diagnosis_messages": [],
        }
        result = await diagnose_node(state)
        assert result["diagnosis_summary"] == "Pod OOMKilled, memory limit too low"
        assert result["confidence"] == 0.85
        assert result["evidence"] == {"k8s.describe_pod": [{"phase": "CrashLoopBackOff"}]}


@pytest.mark.asyncio
async def test_diagnose_loop_end_turn_immediately() -> None:
    """LLM returns final analysis on first turn (no tool calls)."""
    from app.llm import LLMResponse

    state = _make_state()

    llm_response = LLMResponse(
        text="Pod is CrashLoopBackOff due to OOMKilled",
        tool_uses=[],
        stop_reason="end_turn",
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=llm_response)

    with (
        patch("app.graph.nodes.diagnose.build_llm_client", return_value=mock_client),
        patch("app.graph.nodes.diagnose.get_settings"),
        patch("app.graph.nodes.diagnose.global_registry") as mock_registry,
    ):
        mock_registry.as_tool_specs.return_value = []
        result = await run_diagnose_loop(state)

        assert result["diagnosis_summary"] == "Pod is CrashLoopBackOff due to OOMKilled"
        assert result["confidence"] == 0.8
        assert result["evidence"] == {}


@pytest.mark.asyncio
async def test_diagnose_loop_tool_use_then_end_turn() -> None:
    """LLM calls a tool on first turn, then gives final analysis."""
    from app.llm import LLMResponse, ToolUse
    from app.plugins.base import PluginResult

    state = _make_state()

    tool_use = ToolUse(id="tu_1", name="k8s.describe_pod", input={"pod": "order-api-abc"})
    first_response = LLMResponse(
        text="Let me check the pod status.",
        tool_uses=[tool_use],
        stop_reason="tool_use",
    )
    second_response = LLMResponse(
        text="Pod OOMKilled, increase memory limit.",
        tool_uses=[],
        stop_reason="end_turn",
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=[first_response, second_response])

    mock_plugin = AsyncMock()
    mock_plugin.execute = AsyncMock(
        return_value=PluginResult(
            ok=True,
            output={"phase": "CrashLoopBackOff", "reason": "OOMKilled"},
        )
    )

    with (
        patch("app.graph.nodes.diagnose.build_llm_client", return_value=mock_client),
        patch("app.graph.nodes.diagnose.get_settings"),
        patch("app.graph.nodes.diagnose.global_registry") as mock_registry,
    ):
        mock_registry.as_tool_specs.return_value = []
        mock_registry.get.return_value = mock_plugin

        result = await run_diagnose_loop(state)

        assert result["diagnosis_summary"] == "Pod OOMKilled, increase memory limit."
        assert result["confidence"] == 0.8
        assert "k8s.describe_pod" in result["evidence"]
        assert mock_plugin.execute.call_count == 1


@pytest.mark.asyncio
async def test_diagnose_loop_max_turns_reached() -> None:
    """LLM keeps calling tools until max_turns is exhausted."""
    from app.llm import LLMResponse, ToolUse
    from app.plugins.base import PluginResult

    state = _make_state()

    tool_use = ToolUse(id="tu_1", name="k8s.describe_pod", input={"pod": "order-api-abc"})
    # Always return tool_use, never end_turn
    always_tool_response = LLMResponse(
        text="Still investigating...",
        tool_uses=[tool_use],
        stop_reason="tool_use",
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=always_tool_response)

    mock_plugin = AsyncMock()
    mock_plugin.execute = AsyncMock(
        return_value=PluginResult(
            ok=True,
            output={"phase": "Running"},
        )
    )

    with (
        patch("app.graph.nodes.diagnose.build_llm_client", return_value=mock_client),
        patch("app.graph.nodes.diagnose.get_settings"),
        patch("app.graph.nodes.diagnose.global_registry") as mock_registry,
    ):
        mock_registry.as_tool_specs.return_value = []
        mock_registry.get.return_value = mock_plugin

        result = await run_diagnose_loop(state, max_turns=3)

        assert result["diagnosis_summary"] == "诊断超时,未能收敛"
        assert result["confidence"] == 0.3
        assert mock_client.complete.call_count == 3


@pytest.mark.asyncio
async def test_diagnose_loop_handles_plugin_error() -> None:
    """Plugin execution error is caught and reported back to LLM."""
    from app.llm import LLMResponse, ToolUse

    state = _make_state()

    tool_use = ToolUse(id="tu_1", name="k8s.describe_pod", input={"pod": "order-api-abc"})
    first_response = LLMResponse(
        text="Let me check.",
        tool_uses=[tool_use],
        stop_reason="tool_use",
    )
    second_response = LLMResponse(
        text="Could not get pod info, but likely OOM.",
        tool_uses=[],
        stop_reason="end_turn",
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=[first_response, second_response])

    mock_plugin = AsyncMock()
    mock_plugin.execute = AsyncMock(side_effect=RuntimeError("k8s API timeout"))

    with (
        patch("app.graph.nodes.diagnose.build_llm_client", return_value=mock_client),
        patch("app.graph.nodes.diagnose.get_settings"),
        patch("app.graph.nodes.diagnose.global_registry") as mock_registry,
    ):
        mock_registry.as_tool_specs.return_value = []
        mock_registry.get.return_value = mock_plugin

        result = await run_diagnose_loop(state)

        assert result["diagnosis_summary"] == "Could not get pod info, but likely OOM."
        # evidence should NOT contain the failed tool call
        assert "k8s.describe_pod" not in result["evidence"]

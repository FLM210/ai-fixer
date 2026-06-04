import pytest

from app.llm.base import (
    LLMClient,
    LLMMessage,
    LLMResponse,
    ToolResult,
    ToolSpec,
    ToolUse,
)


def test_message_roles() -> None:
    msg = LLMMessage(role="user", content="hi")
    assert msg.role == "user"
    assert msg.content == "hi"


def test_tool_spec_validates_schema() -> None:
    spec = ToolSpec(
        name="k8s.describe_pod",
        description="describe pod",
        input_schema={
            "type": "object",
            "properties": {"pod": {"type": "string"}},
            "required": ["pod"],
        },
    )
    assert spec.name == "k8s.describe_pod"


def test_tool_use_and_result_round_trip() -> None:
    tu = ToolUse(id="t1", name="x", input={"a": 1})
    tr = ToolResult(tool_use_id="t1", content={"ok": True}, is_error=False)
    assert tu.id == tr.tool_use_id


def test_llm_client_is_abstract() -> None:
    with pytest.raises(TypeError):
        LLMClient()  # type: ignore[abstract]


def test_llm_response_can_carry_tool_uses() -> None:
    resp = LLMResponse(
        text="thinking",
        tool_uses=[ToolUse(id="t1", name="n", input={})],
        stop_reason="tool_use",
        usage={"input_tokens": 10, "output_tokens": 5},
    )
    assert resp.stop_reason == "tool_use"
    assert resp.tool_uses[0].id == "t1"

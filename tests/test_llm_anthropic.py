from typing import Any

import httpx
import pytest
import respx

from app.llm import LLMMessage, ToolSpec
from app.llm.anthropic_client import AnthropicClient


def _success_payload(*, with_tool: bool = False) -> dict[str, Any]:
    if with_tool:
        return {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "thinking"},
                {"type": "tool_use", "id": "tu_1", "name": "k8s.describe_pod",
                 "input": {"pod": "p", "namespace": "n"}},
            ],
            "model": "claude-sonnet-4-6",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "hello"}],
        "model": "claude-sonnet-4-6",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 5, "output_tokens": 3},
    }


@pytest.mark.asyncio
@respx.mock
async def test_anthropic_text_response() -> None:
    respx.post("https://example.com/v1/messages").mock(
        return_value=httpx.Response(200, json=_success_payload())
    )
    client = AnthropicClient(
        base_url="https://example.com",
        api_key="sk-test",
        model="claude-sonnet-4-6",
        timeout_seconds=10,
    )
    resp = await client.complete(
        system="be helpful",
        messages=[LLMMessage(role="user", content="hi")],
    )
    assert resp.text == "hello"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 3}
    assert resp.tool_uses == []


@pytest.mark.asyncio
@respx.mock
async def test_anthropic_tool_use_response() -> None:
    respx.post("https://example.com/v1/messages").mock(
        return_value=httpx.Response(200, json=_success_payload(with_tool=True))
    )
    client = AnthropicClient(
        base_url="https://example.com",
        api_key="sk-test",
        model="claude-sonnet-4-6",
        timeout_seconds=10,
    )
    resp = await client.complete(
        system="be helpful",
        messages=[LLMMessage(role="user", content="describe pod")],
        tools=[ToolSpec(
            name="k8s.describe_pod",
            description="describe a pod",
            input_schema={
                "type": "object",
                "properties": {"pod": {"type": "string"}, "namespace": {"type": "string"}},
                "required": ["pod", "namespace"],
            },
        )],
    )
    assert resp.stop_reason == "tool_use"
    assert len(resp.tool_uses) == 1
    assert resp.tool_uses[0].name == "k8s.describe_pod"
    assert resp.tool_uses[0].input == {"pod": "p", "namespace": "n"}


@pytest.mark.asyncio
@respx.mock
async def test_anthropic_error_propagates() -> None:
    respx.post("https://example.com/v1/messages").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    client = AnthropicClient(
        base_url="https://example.com",
        api_key="sk-test",
        model="claude-sonnet-4-6",
        timeout_seconds=10,
    )
    with pytest.raises(Exception):
        await client.complete(system="s", messages=[LLMMessage(role="user", content="hi")])


def test_anthropic_provider_and_model() -> None:
    client = AnthropicClient(
        base_url="https://example.com",
        api_key="sk-test",
        model="claude-sonnet-4-6",
        timeout_seconds=10,
    )
    assert client.provider == "anthropic"
    assert client.model == "claude-sonnet-4-6"

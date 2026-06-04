import json
from typing import Any

import httpx
import pytest
import respx

from app.llm import LLMMessage, ToolSpec
from app.llm.openai_client import OpenAIClient


def _success_payload(*, with_tool: bool = False) -> dict[str, Any]:
    if with_tool:
        return {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "k8s.describe_pod",
                            "arguments": json.dumps({"pod": "p", "namespace": "n"}),
                        },
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "hello"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }


@pytest.mark.asyncio
@respx.mock
async def test_openai_text_response() -> None:
    respx.post("https://example.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_success_payload())
    )
    client = OpenAIClient(
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        timeout_seconds=10,
    )
    resp = await client.complete(
        system="be helpful",
        messages=[LLMMessage(role="user", content="hi")],
    )
    assert resp.text == "hello"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 3}


@pytest.mark.asyncio
@respx.mock
async def test_openai_tool_call_response() -> None:
    respx.post("https://example.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_success_payload(with_tool=True))
    )
    client = OpenAIClient(
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
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
    assert resp.tool_uses[0].id == "call_1"
    assert resp.tool_uses[0].name == "k8s.describe_pod"
    assert resp.tool_uses[0].input == {"pod": "p", "namespace": "n"}


@pytest.mark.asyncio
@respx.mock
async def test_openai_error_propagates() -> None:
    respx.post("https://example.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    client = OpenAIClient(
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        timeout_seconds=10,
    )
    with pytest.raises(Exception):
        await client.complete(system="s", messages=[LLMMessage(role="user", content="hi")])


def test_openai_provider_and_model() -> None:
    client = OpenAIClient(
        base_url="https://example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        timeout_seconds=10,
    )
    assert client.provider == "openai"
    assert client.model == "gpt-4o"

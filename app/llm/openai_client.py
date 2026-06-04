import json
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.llm.base import LLMClient, LLMMessage, LLMResponse, ToolSpec, ToolUse

_STOP_REASON_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "function_call": "tool_use",
    "content_filter": "stop_sequence",
}


class OpenAIClient(LLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._sdk = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[LLMMessage],
        tools: Sequence[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        openai_messages = self._to_openai_messages(system, messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        resp: ChatCompletion = await self._sdk.chat.completions.create(**kwargs)
        return self._normalize(resp)

    @staticmethod
    def _to_openai_messages(
        system: str, messages: Sequence[LLMMessage]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                # tool 角色消息需要关联 tool_call_id
                out.append({
                    "role": "tool",
                    "tool_call_id": m.tool_use_id or "",
                    "content": m.content if isinstance(m.content, str) else json.dumps(m.content),
                })
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    @staticmethod
    def _normalize(resp: ChatCompletion) -> LLMResponse:
        choice = resp.choices[0]
        msg = choice.message

        text = msg.content or ""
        tool_uses: list[ToolUse] = []
        if msg.tool_calls:
            for call in msg.tool_calls:
                if call.type == "function":
                    try:
                        args = json.loads(call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    tool_uses.append(ToolUse(id=call.id, name=call.function.name, input=args))

        finish_reason = choice.finish_reason or "stop"
        stop_reason = _STOP_REASON_MAP.get(finish_reason, "end_turn")

        usage = {}
        if resp.usage:
            usage = {
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }

        return LLMResponse(
            text=text,
            tool_uses=tool_uses,
            stop_reason=stop_reason,
            usage=usage,
            raw=resp.model_dump(),
        )

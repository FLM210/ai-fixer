from collections.abc import Sequence
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam

from app.llm.base import LLMClient, LLMMessage, LLMResponse, ToolSpec, ToolUse


class AnthropicClient(LLMClient):
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
        self._sdk = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=1,
        )

    @property
    def provider(self) -> str:
        return "anthropic"

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
        anthropic_messages = self._to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "system": system,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]

        resp: Message = await self._sdk.messages.create(**kwargs)
        return self._normalize(resp)

    @staticmethod
    def _to_anthropic_messages(messages: Sequence[LLMMessage]) -> list[MessageParam]:
        out: list[MessageParam] = []
        for m in messages:
            if m.role == "system":
                # system 由 kwargs.system 单独传入,这里跳过
                continue
            if m.role == "tool":
                # 工具结果必须用 tool_result 格式，关联 tool_use_id
                content = m.content if isinstance(m.content, str) else str(m.content)
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_use_id or "",
                                "content": content,
                            }
                        ],
                    }
                )
            elif m.role == "assistant":
                out.append({"role": "assistant", "content": m.content})
            else:
                out.append({"role": "user", "content": m.content})
        return out

    @staticmethod
    def _normalize(resp: Message) -> LLMResponse:
        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(
                    ToolUse(
                        id=block.id,
                        name=block.name,
                        input=dict(block.input) if isinstance(block.input, dict) else {},
                    )
                )
        return LLMResponse(
            text="".join(text_parts),
            tool_uses=tool_uses,
            stop_reason=resp.stop_reason or "end_turn",
            usage={
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
            raw=resp.model_dump(),
        )

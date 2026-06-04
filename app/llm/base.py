from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]]
    tool_use_id: str | None = None


class ToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    input_schema: dict[str, Any]


class ToolUse(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    input: dict[str, Any]


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_use_id: str
    content: dict[str, Any] | str
    is_error: bool = False


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    tool_uses: list[ToolUse] = Field(default_factory=list)
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "error"]
    usage: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        messages: Sequence[LLMMessage],
        tools: Sequence[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """单轮(可携带工具)调用,返回归一化 LLMResponse。"""

    @property
    @abstractmethod
    def provider(self) -> str:
        """返回 provider 名(anthropic / openai)。"""

    @property
    @abstractmethod
    def model(self) -> str:
        """返回当前 model 名。"""

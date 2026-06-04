from abc import ABC, abstractmethod
from typing import Any, Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

PluginCategory = Literal["diagnostic", "remediation", "fallback"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ResourceType = Literal["k8s", "database", "cloud", "network", "system"]


class PluginSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = Field(..., min_length=1, pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    category: PluginCategory
    resource_type: ResourceType = "k8s"
    description: str = Field(..., min_length=1)
    risk_level: RiskLevel
    requires_approval: bool = False
    blast_radius: str = ""
    timeout_seconds: float = Field(..., gt=0)
    input_schema: dict[str, Any]


class PluginContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    incident_id: str
    actor: str  # agent | user_id
    trace_id: str
    dry_run: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class PluginResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    ok: bool
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_snippets: list[str] = Field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0


class Plugin(ABC):
    @property
    @abstractmethod
    def spec(self) -> PluginSpec: ...

    @abstractmethod
    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult: ...

    def validate_args(self, args: dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=args, schema=self.spec.input_schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"invalid plugin args for {self.spec.name}: {e.message}") from e

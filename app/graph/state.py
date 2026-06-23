from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict


class ProposalDraft(TypedDict):
    plugin_name: str
    args: dict[str, Any]
    risk_level: Literal["low", "medium", "high", "critical"]
    description: str
    expected_outcome: str | None
    rollback_hint: str | None
    source: Literal["plugin", "llm_fallback"]


class PolicyDecision(TypedDict):
    proposal_index: int
    decision: Literal["auto_execute", "require_approval", "escalate"]
    reason: str


class ExecutionRecord(TypedDict):
    proposal_id: str
    plugin_name: str
    status: Literal["success", "failure", "timeout"]
    output: dict[str, Any]
    error: str | None
    duration_ms: int


class GraphState(TypedDict):
    # 标识
    incident_id: str
    trace_id: str

    # 输入
    raw_alert: str
    source_meta: dict[str, Any]  # {chat_id, msg_id, sender, ts}

    # Triage 阶段产出
    category: str | None
    severity: Literal["p0", "p1", "p2", "p3"] | None
    service: str | None
    is_duplicate: bool

    # Diagnose 阶段产出
    diagnosis_messages: list[Any]
    evidence: dict[str, Any]
    diagnosis_summary: str | None
    confidence: float | None
    similar_incidents: list[dict[str, Any]]  # 历史相似 incident

    # Propose 阶段产出
    proposals: list[ProposalDraft]

    # Policy 阶段产出
    policy_decisions: list[PolicyDecision]

    # Approval 阶段
    approval_decisions: dict[str, str]  # {proposal_id: 'approved'/'rejected'}
    awaiting_since: datetime | None

    # 诊断确认阶段
    diagnosis_approved: bool | None
    proposals_approved: bool | None

    # Execute 阶段
    execution_results: list[ExecutionRecord]

    # 生产环境上下文
    env_context: str | None

    # LLM 对话记录（所有阶段）
    llm_turns: list[dict[str, Any]]
    llm_cost_tokens: int

    # 终态
    final_status: str | None

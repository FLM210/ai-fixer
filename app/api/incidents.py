"""Incident 查询 API。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models.diagnosis import Diagnosis
from app.db.models.fix_execution import FixExecution
from app.db.models.fix_proposal import FixProposal
from app.db.models.incident import Incident

router = APIRouter()


class IncidentSummary(BaseModel):
    id: str
    fingerprint: str
    status: str
    category: str | None
    severity: str | None
    service: str | None
    namespace: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolution_type: str | None
    confidence: float | None
    proposal_count: int


class IncidentListResponse(BaseModel):
    items: list[IncidentSummary]
    total: int
    page: int
    page_size: int


class DiagnosisDetail(BaseModel):
    root_cause: str | None
    confidence: float | None
    evidence: list[Any] | None
    created_at: datetime


class ProposalDetail(BaseModel):
    id: str
    plugin_name: str
    risk_level: str | None
    description: str | None
    expected_outcome: str | None
    args: dict[str, Any] | None
    source: str | None


class ExecutionDetail(BaseModel):
    id: str
    proposal_id: str
    status: str
    approved_by: str | None
    output: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class LLMTurnDetail(BaseModel):
    id: str
    phase: str
    turn_index: int
    role: str
    content: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    created_at: datetime


class IncidentDetail(BaseModel):
    id: str
    fingerprint: str
    status: str
    category: str | None
    severity: str | None
    service: str | None
    namespace: str | None
    summary: str | None
    raw_alert: dict[str, Any]
    chat_id: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolution_type: str | None
    llm_cost_tokens: int | None
    diagnosis: DiagnosisDetail | None
    proposals: list[ProposalDetail]
    executions: list[ExecutionDetail]
    llm_turns: list[LLMTurnDetail]


@router.get("/incidents")
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> IncidentListResponse:
    """获取 Incident 列表（分页、筛选）。"""
    # 构建查询
    stmt = select(Incident)
    count_stmt = select(func.count()).select_from(Incident)

    if status:
        stmt = stmt.where(Incident.status == status)
        count_stmt = count_stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
        count_stmt = count_stmt.where(Incident.severity == severity)

    # 总数
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    stmt = stmt.order_by(Incident.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    incidents = result.scalars().all()

    # 批量查询每个 incident 的 proposal 数和 diagnosis 置信度
    items = []
    for inc in incidents:
        # proposal count
        prop_stmt = select(func.count()).select_from(FixProposal).where(
            FixProposal.incident_id == inc.id
        )
        prop_result = await session.execute(prop_stmt)
        proposal_count = prop_result.scalar() or 0

        # confidence
        diag_stmt = select(Diagnosis.confidence).where(Diagnosis.incident_id == inc.id).limit(1)
        diag_result = await session.execute(diag_stmt)
        confidence = diag_result.scalar()

        items.append(IncidentSummary(
            id=str(inc.id),
            fingerprint=inc.fingerprint,
            status=inc.status,
            category=inc.category,
            severity=inc.severity,
            service=inc.service,
            namespace=inc.namespace,
            summary=inc.summary,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            resolved_at=inc.resolved_at,
            resolution_type=inc.resolution_type,
            confidence=confidence,
            proposal_count=proposal_count,
        ))

    return IncidentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> IncidentDetail:
    """获取 Incident 详情（含 diagnosis、proposals、executions）。"""
    # Incident
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await session.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")

    # Diagnosis
    diag_stmt = select(Diagnosis).where(Diagnosis.incident_id == incident_id)
    diag_result = await session.execute(diag_stmt)
    diagnosis = diag_result.scalar_one_or_none()
    diagnosis_detail = None
    if diagnosis:
        diagnosis_detail = DiagnosisDetail(
            root_cause=diagnosis.root_cause,
            confidence=diagnosis.confidence,
            evidence=diagnosis.evidence,
            created_at=diagnosis.created_at,
        )

    # Proposals
    prop_stmt = select(FixProposal).where(FixProposal.incident_id == incident_id)
    prop_result = await session.execute(prop_stmt)
    proposals = [
        ProposalDetail(
            id=str(p.id),
            plugin_name=p.plugin_name,
            risk_level=p.risk_level,
            description=p.description,
            expected_outcome=p.expected_outcome,
            args=p.args,
            source=p.source,
        )
        for p in prop_result.scalars().all()
    ]

    # Executions
    exec_stmt = select(FixExecution).where(FixExecution.incident_id == incident_id)
    exec_result = await session.execute(exec_stmt)
    executions = [
        ExecutionDetail(
            id=str(e.id),
            proposal_id=str(e.proposal_id),
            status=e.status,
            approved_by=e.approved_by,
            output=e.output,
            error=e.error,
            started_at=e.started_at,
            finished_at=e.finished_at,
        )
        for e in exec_result.scalars().all()
    ]

    # LLM Turns
    from app.db.models.llm_turn import LLMTurn
    turns_stmt = select(LLMTurn).where(LLMTurn.incident_id == incident_id).order_by(LLMTurn.turn_index)
    turns_result = await session.execute(turns_stmt)
    llm_turns = [
        LLMTurnDetail(
            id=str(t.id),
            phase=t.phase,
            turn_index=t.turn_index,
            role=t.role,
            content=t.content,
            tool_name=t.tool_name,
            tool_input=t.tool_input,
            created_at=t.created_at,
        )
        for t in turns_result.scalars().all()
    ]

    return IncidentDetail(
        id=str(incident.id),
        fingerprint=incident.fingerprint,
        status=incident.status,
        category=incident.category,
        severity=incident.severity,
        service=incident.service,
        namespace=incident.namespace,
        summary=incident.summary,
        raw_alert=incident.raw_alert,
        chat_id=incident.chat_id,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        resolution_type=incident.resolution_type,
        llm_cost_tokens=incident.llm_cost_tokens,
        diagnosis=diagnosis_detail,
        proposals=proposals,
        executions=executions,
        llm_turns=llm_turns,
    )

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import session_scope
from app.db.models import Incident, IncidentEvent, IncidentStatus
from app.graph.state import GraphState


def generate_fingerprint(raw_alert: str, category: str | None, service: str | None) -> str:
    """根据告警文本生成 fingerprint,用于去重判断。

    当前简化版: 对告警文本做 sha256 取前 16 位。
    后续应提取 category + service + 关键 metric 名 + 错误关键词。
    """
    normalized = raw_alert.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def create_incident(state: GraphState) -> dict[str, object]:
    """创建 incident 记录或检测到重复时追加事件。

    Returns:
        dict with keys: id (str), fingerprint (str), is_duplicate (bool)
    """
    fingerprint = generate_fingerprint(
        state["raw_alert"], state.get("category"), state.get("service")
    )

    async with session_scope() as session:
        # 检查重复: 最近 30 分钟内同 fingerprint 且未解决/忽略的 incident
        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        result = await session.execute(
            select(Incident).where(
                Incident.fingerprint == fingerprint,
                Incident.created_at >= cutoff,
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.IGNORED]),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 追加重复检测事件到已有 incident
            session.add(
                IncidentEvent(
                    incident_id=existing.id,
                    event_type="duplicate_detected",
                    payload={"new_alert": state["raw_alert"]},
                    actor="system",
                )
            )
            return {"id": str(existing.id), "fingerprint": fingerprint, "is_duplicate": True}

        # 创建新 incident
        incident = Incident(
            fingerprint=fingerprint,
            status=IncidentStatus.NEW,
            raw_alert={"text": state["raw_alert"], "source": state["source_meta"]},
            chat_id=state["source_meta"].get("chat_id"),
            source_message_id=state["source_meta"].get("msg_id"),
        )
        session.add(incident)
        await session.flush()

        session.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="created",
                payload={"raw_alert": state["raw_alert"]},
                actor="system",
            )
        )

        return {"id": str(incident.id), "fingerprint": fingerprint, "is_duplicate": False}


async def ingest_node(state: GraphState) -> GraphState:
    """ingest 节点: 创建 incident 记录,生成 fingerprint,检查重复。"""
    result = await create_incident(state)
    state["incident_id"] = str(result["id"])
    state["is_duplicate"] = bool(result.get("is_duplicate", False))
    return state

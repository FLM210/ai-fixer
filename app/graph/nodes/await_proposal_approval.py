"""修复方案确认节点：发送方案卡片，等待用户确认后继续。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.types import interrupt

from app.graph.state import GraphState
from app.lark.card_sender import send_proposal_confirm_card

logger = logging.getLogger(__name__)


async def await_proposal_approval_node(state: GraphState) -> GraphState:
    """发送修复方案卡片，使用 interrupt() 暂停工作流等待用户确认。"""
    chat_id = state["source_meta"].get("chat_id", "")
    incident_id = state["incident_id"]

    already_sent = state.get("awaiting_since") is not None
    state["awaiting_since"] = datetime.now(UTC)

    if not already_sent:
        try:
            logger.info("发送方案确认卡片: incident=%s chat=%s", incident_id, chat_id)
            await send_proposal_confirm_card(
                chat_id=chat_id,
                incident_id=incident_id,
                diagnosis=state.get("diagnosis_summary") or "无诊断结果",
                confidence=state.get("confidence") or 0,
                category=state.get("category") or "unknown",
                severity=state.get("severity") or "unknown",
                proposals=state.get("proposals", []),
                policy_decisions=state.get("policy_decisions", []),
            )
        except Exception:
            logger.warning("发送方案确认卡片失败", exc_info=True)
    else:
        logger.info("恢复执行，跳过方案卡片发送")

    response: dict[str, Any] = interrupt(
        {"type": "proposal_approval", "incident_id": incident_id}
    )

    action = response.get("action", "reject")
    state["proposals_approved"] = action == "approve"

    if state["proposals_approved"]:
        state["approval_decisions"] = {
            f"prop-{i}": "approved"
            for i in range(len(state.get("proposals", [])))
        }

    logger.info("方案确认结果: action=%s", action)
    return state

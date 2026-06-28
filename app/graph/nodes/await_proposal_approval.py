"""修复方案确认节点：等待用户确认修复方案。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.types import interrupt

from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def send_proposal_card_node(state: GraphState, config: dict[str, Any]) -> GraphState:
    """发送方案确认卡片（独立节点，state 修改会被 checkpoint 保存）。"""
    from app.lark.card_sender import send_proposal_confirm_card

    chat_id = state["source_meta"].get("chat_id", "")
    incident_id = state["incident_id"]
    thread_id = config.get("configurable", {}).get("thread_id", "")

    try:
        logger.info("发送方案确认卡片: incident=%s chat=%s", incident_id, chat_id)
        await send_proposal_confirm_card(
            chat_id=chat_id,
            incident_id=incident_id,
            thread_id=thread_id,
            diagnosis=state.get("diagnosis_summary") or "无诊断结果",
            confidence=state.get("confidence") or 0,
            category=state.get("category") or "unknown",
            severity=state.get("severity") or "unknown",
            proposals=state.get("proposals", []),
            policy_decisions=state.get("policy_decisions", []),
            source_message_id=state.get("source_meta", {}).get("msg_id", ""),
        )
    except Exception:
        logger.warning("发送方案确认卡片失败", exc_info=True)

    return state


async def await_proposal_approval_node(state: GraphState) -> GraphState:
    """暂停工作流，等待用户通过飞书卡片确认修复方案。"""
    logger.info("=== await_proposal_approval: 等待用户确认 ===")
    incident_id = state["incident_id"]

    response: dict[str, Any] = interrupt(
        {"type": "proposal_approval", "incident_id": incident_id}
    )

    action = response.get("action", "reject")
    state["proposals_approved"] = action == "approve"
    state["awaiting_since"] = datetime.now(UTC)

    if state["proposals_approved"]:
        state["approval_decisions"] = {
            f"prop-{i}": "approved"
            for i in range(len(state.get("proposals", [])))
        }

    logger.info("方案确认结果: action=%s", action)
    return state

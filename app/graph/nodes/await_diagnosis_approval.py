"""诊断确认节点：等待用户确认诊断结果。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.types import interrupt

from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def send_diagnosis_card_node(state: GraphState, config: dict[str, Any]) -> GraphState:
    """发送诊断确认卡片（独立节点，state 修改会被 checkpoint 保存）。"""
    from app.lark.card_sender import send_diagnosis_confirm_card

    chat_id = state["source_meta"].get("chat_id", "")
    incident_id = state["incident_id"]
    thread_id = config.get("configurable", {}).get("thread_id", "")

    try:
        logger.info("发送诊断确认卡片: incident=%s chat=%s", incident_id, chat_id)
        await send_diagnosis_confirm_card(
            chat_id=chat_id,
            incident_id=incident_id,
            thread_id=thread_id,
            diagnosis=state.get("diagnosis_summary") or "无诊断结果",
            confidence=state.get("confidence") or 0,
            category=state.get("category") or "unknown",
            severity=state.get("severity") or "unknown",
            service=state.get("service") or "unknown",
            evidence=state.get("evidence", {}),
            source_message_id=state.get("source_meta", {}).get("msg_id", ""),
        )
    except Exception:
        logger.warning("发送诊断确认卡片失败", exc_info=True)

    return state


async def await_diagnosis_approval_node(state: GraphState) -> GraphState:
    """暂停工作流，等待用户通过飞书卡片确认诊断结果。"""
    logger.info("=== await_diagnosis_approval: 等待用户确认 ===")
    incident_id = state["incident_id"]

    # interrupt() 暂停工作流，等待 resume value
    response: dict[str, Any] = interrupt(
        {"type": "diagnosis_approval", "incident_id": incident_id}
    )

    action = response.get("action", "reject")
    state["diagnosis_approved"] = action == "approve"
    state["awaiting_since"] = datetime.now(UTC)
    logger.info("诊断确认结果: action=%s", action)

    return state

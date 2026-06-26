"""诊断确认节点：发送诊断结果卡片，等待用户确认后继续。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.types import interrupt

from app.graph.state import GraphState
from app.lark.card_sender import send_diagnosis_confirm_card

logger = logging.getLogger(__name__)


async def await_diagnosis_approval_node(state: GraphState) -> GraphState:
    """发送诊断结果卡片，使用 interrupt() 暂停工作流等待用户确认。"""
    logger.info("=== await_diagnosis_approval 节点开始执行 ===")
    chat_id = state["source_meta"].get("chat_id", "")
    incident_id = state["incident_id"]

    # 设置标记（必须在 interrupt 之前，确保 checkpoint 保存）
    # 恢复执行时此值已存在，用于跳过卡片发送
    already_sent = state.get("awaiting_since") is not None
    state["awaiting_since"] = datetime.now(UTC)

    if not already_sent:
        # 首次执行：发送诊断确认卡片
        try:
            logger.info("发送诊断确认卡片: incident=%s chat=%s", incident_id, chat_id)
            await send_diagnosis_confirm_card(
                chat_id=chat_id,
                incident_id=incident_id,
                diagnosis=state.get("diagnosis_summary") or "无诊断结果",
                confidence=state.get("confidence") or 0,
                category=state.get("category") or "unknown",
                severity=state.get("severity") or "unknown",
                service=state.get("service") or "unknown",
                evidence=state.get("evidence", {}),
            )
        except Exception:
            logger.warning("发送诊断确认卡片失败", exc_info=True)
    else:
        logger.info("恢复执行，跳过卡片发送")

    # 暂停工作流，等待用户确认
    response: dict[str, Any] = interrupt(
        {"type": "diagnosis_approval", "incident_id": incident_id}
    )

    # 根据用户回复设置确认状态
    action = response.get("action", "reject")
    state["diagnosis_approved"] = action == "approve"
    logger.info("诊断确认结果: action=%s", action)

    return state

"""飞书 HTTP Webhook 事件接收端点。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lark/event")
async def lark_event(request: Request) -> dict:
    body = await request.json()

    # URL 验证
    if body.get("type") == "url_verification":
        logger.info("飞书 URL 验证请求")
        return {"challenge": body.get("challenge", "")}

    header = body.get("header", {})
    event_type = header.get("event_type", "")

    if event_type == "im.message.receive_v1":
        await _handle_message_event(body.get("event", {}))

    return {"code": 0}


@router.post("/lark/card/action")
async def lark_card_action(request: Request) -> dict:
    """处理卡片按钮点击回调。"""
    body = await request.json()

    # 提取 action 信息
    action = body.get("action", {})
    value = action.get("value", {})
    open_id = body.get("open_id", "")

    action_type = value.get("action", "")
    incident_id = value.get("incident_id", "")

    logger.info("卡片回调: action=%s incident=%s user=%s", action_type, incident_id, open_id)

    if action_type == "approve":
        asyncio.create_task(_handle_approval(incident_id, open_id))
        return {"toast": {"type": "success", "content": "已批准，正在执行修复..."}}
    elif action_type == "reject":
        asyncio.create_task(_handle_rejection(incident_id, open_id))
        return {"toast": {"type": "info", "content": "已拒绝"}}

    return {"toast": {"type": "warning", "content": "未知操作"}}


async def _handle_message_event(event: dict) -> None:
    """处理消息事件：分析是否为告警，触发工作流。"""
    try:
        message = event.get("message", {})
        sender = event.get("sender", {})

        chat_id = message.get("chat_id", "")
        msg_type = message.get("message_type", message.get("msg_type", ""))
        content = message.get("content", "")
        message_id = message.get("message_id", "")

        # 提取 sender_id
        sender_id_obj = sender.get("sender_id", {})
        sender_id = sender_id_obj.get("open_id", "") or sender_id_obj.get("user_id", "")

        # 只处理文本、卡片、富文本
        if msg_type not in ("text", "post", "interactive"):
            return

        text = _extract_text_from_content(content, msg_type)
        if not text:
            return

        # 检测是否为告警
        from app.config import get_settings
        from app.lark.detector import AlertDetector

        settings = get_settings()
        detector = AlertDetector(alert_bot_ids=settings.alert_bot_ids)

        if not detector.is_alert(text, sender_id):
            return

        logger.info("检测到告警，触发工作流: chat=%s sender=%s", chat_id, sender_id)

        # 异步触发工作流
        loop = asyncio.get_running_loop()
        loop.create_task(_trigger_workflow(text, chat_id, message_id, sender_id))

    except Exception:
        logger.exception("处理消息事件异常")


def _extract_text_from_content(content: str, msg_type: str) -> str:
    if not content:
        return ""
    try:
        data = json.loads(content)
        if msg_type == "text":
            return data.get("text", "")
        if msg_type == "interactive":
            parts = []
            title = data.get("title", "")
            if isinstance(title, dict):
                title = title.get("content", "")
            if title:
                parts.append(title)
            _extract_card_text(data, parts)
            return "\n".join(parts)
        if msg_type == "post":
            parts = []
            for lang_content in data.values():
                if isinstance(lang_content, dict):
                    for line in lang_content.get("content", []):
                        for elem in line:
                            if elem.get("tag") == "text":
                                parts.append(elem.get("text", ""))
            return "\n".join(parts)
    except (json.JSONDecodeError, TypeError):
        return content
    return ""


# 临时存储待审批的 incident（生产环境应用 Redis/DB）
_pending_incidents: dict[str, dict[str, Any]] = {}


async def _handle_approval(incident_id: str, user_id: str) -> None:
    """处理审批通过：执行修复操作。"""
    from app.lark.card_sender import send_result_card, send_text_message

    pending = _pending_incidents.get(incident_id)
    if not pending:
        logger.warning("未找到待审批 incident: %s", incident_id)
        return

    chat_id = pending.get("chat_id", "")
    proposals = pending.get("proposals", [])
    diagnosis = pending.get("diagnosis", "")

    logger.info("执行修复: incident=%s user=%s", incident_id, user_id)

    # 执行所有提案
    from app.plugins import PluginContext, global_registry
    from app.graph.nodes.execute import execute_plugin
    from app.graph.state import GraphState

    state: GraphState = pending.get("state", {})
    results = []
    for i, proposal in enumerate(proposals):
        try:
            ctx = PluginContext(
                incident_id=incident_id,
                actor=user_id,
                trace_id=state.get("trace_id", ""),
            )
            plugin = global_registry.get(proposal["plugin_name"])
            result = await plugin.execute(ctx, proposal.get("args", {}))
            results.append({
                "plugin_name": proposal["plugin_name"],
                "status": "success" if result.ok else "failure",
                "output": result.output,
                "error": result.error,
            })
        except Exception as e:
            results.append({
                "plugin_name": proposal.get("plugin_name", "unknown"),
                "status": "failure",
                "error": str(e),
            })

    # 发送结果卡片
    await send_result_card(
        chat_id=chat_id,
        incident_id=incident_id,
        diagnosis=diagnosis,
        execution_results=results,
        auto_resolved=False,
    )

    # 清理
    _pending_incidents.pop(incident_id, None)


async def _handle_rejection(incident_id: str, user_id: str) -> None:
    """处理审批拒绝。"""
    from app.lark.card_sender import send_text_message

    pending = _pending_incidents.pop(incident_id, None)
    if pending:
        chat_id = pending.get("chat_id", "")
        await send_text_message(
            chat_id=chat_id,
            text=f"🚫 修复操作已拒绝\nincident: {incident_id}",
        )


def _extract_card_text(obj: Any, parts: list[str]) -> None:
    if isinstance(obj, dict):
        for key in ("text", "content", "value"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val)
            elif isinstance(val, (dict, list)):
                _extract_card_text(val, parts)
        for elem in obj.get("elements", []):
            _extract_card_text(elem, parts)
        for col in obj.get("columns", []):
            _extract_card_text(col, parts)
    elif isinstance(obj, list):
        for item in obj:
            _extract_card_text(item, parts)


async def _trigger_workflow(
    alert_text: str, chat_id: str, message_id: str, sender_id: str
) -> None:
    """触发工作流并发送结果卡片到群。"""
    from uuid import uuid4

    from app.graph.state import GraphState
    from app.graph.workflow import create_workflow
    from app.lark.card_sender import send_text_message, send_approval_card, send_result_card

    incident_id = str(uuid4())

    initial_state: GraphState = {
        "incident_id": incident_id,
        "trace_id": str(uuid4()),
        "raw_alert": alert_text,
        "source_meta": {
            "chat_id": chat_id,
            "msg_id": message_id,
            "sender": sender_id,
        },
        "category": None,
        "severity": None,
        "service": None,
        "is_duplicate": False,
        "diagnosis_messages": [],
        "evidence": {},
        "diagnosis_summary": None,
        "confidence": None,
        "similar_incidents": [],
        "proposals": [],
        "policy_decisions": [],
        "approval_decisions": {},
        "awaiting_since": None,
        "execution_results": [],
        "final_status": None,
    }

    logger.info("启动工作流: incident=%s", incident_id)

    try:
        workflow = create_workflow()
        app = workflow.compile()
        result = await app.ainvoke(initial_state)

        status = result.get("final_status")
        proposals = result.get("proposals", [])
        policy_decisions = result.get("policy_decisions", [])
        diagnosis = result.get("diagnosis_summary", "")
        confidence = result.get("confidence", 0)
        category = result.get("category", "unknown")
        severity = result.get("severity", "unknown")

        logger.info("工作流完成: incident=%s status=%s", incident_id, status)

        # 根据策略决策发送不同类型的卡片
        has_high_risk = any(
            d.get("decision") == "require_approval" for d in policy_decisions
        )

        if has_high_risk and proposals:
            # 高风险：存储待审批状态并发审批卡片
            _pending_incidents[incident_id] = {
                "chat_id": chat_id,
                "proposals": proposals,
                "diagnosis": diagnosis or "无诊断",
                "state": result,
            }
            await send_approval_card(
                chat_id=chat_id,
                incident_id=incident_id,
                diagnosis=diagnosis or "无诊断",
                confidence=confidence or 0,
                category=category or "unknown",
                severity=severity or "unknown",
                proposals=proposals,
                policy_decisions=policy_decisions,
            )
        elif status == "resolved":
            # 已自动解决：发送结果卡片
            execution_results = result.get("execution_results", [])
            await send_result_card(
                chat_id=chat_id,
                incident_id=incident_id,
                diagnosis=diagnosis or "无诊断",
                execution_results=execution_results,
                auto_resolved=True,
            )
        else:
            # 其他情况：发送诊断摘要
            diag_text = (diagnosis or "无")[:200]
            conf_text = f"{confidence:.0%}" if confidence is not None else "未知"
            await send_text_message(
                chat_id=chat_id,
                text=f"🔍 告警分析完成\n\n"
                     f"分类: {category}\n"
                     f"严重程度: {severity}\n"
                     f"诊断: {diag_text}\n"
                     f"置信度: {conf_text}\n"
                     f"状态: {status}",
            )

    except Exception:
        logger.exception("工作流异常: incident=%s", incident_id)
        await send_text_message(
            chat_id=chat_id,
            text=f"❌ 告警处理异常\nincident: {incident_id}",
        )

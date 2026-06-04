"""飞书消息事件处理器：接收群消息，识别告警，触发工作流。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from app.lark.detector import AlertDetector

logger = logging.getLogger(__name__)


def create_event_handler(
    detector: AlertDetector,
    main_loop: asyncio.AbstractEventLoop | None = None,
) -> lark.EventDispatcherHandler:
    """创建飞书事件处理器。"""

    handler = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(
        _make_message_handler(detector, main_loop)
    ).build()

    return handler


def _make_message_handler(
    detector: AlertDetector,
    main_loop: asyncio.AbstractEventLoop | None = None,
):
    """创建消息接收处理函数（同步回调，内部调度异步工作流）。"""

    def handle_message(data: P2ImMessageReceiveV1) -> None:
        try:
            logger.info("收到飞书事件: %s", type(data).__name__)
            event = data.event
            if not event or not event.message:
                return

            message = event.message
            chat_id = message.chat_id
            msg_type = getattr(message, 'msg_type', None) or getattr(message, 'message_type', '')
            sender = event.sender

            # 提取 sender_id：尝试 open_id、user_id，以及从 sender_type 判断
            sender_id = ""
            if sender:
                sid = getattr(sender, 'sender_id', None)
                if sid:
                    sender_id = getattr(sid, 'open_id', '') or getattr(sid, 'user_id', '') or ""
                # 对于 app 类型的 sender，也尝试提取 app_id
                if not sender_id:
                    sender_id = getattr(sender, 'app_id', '') or getattr(sender, 'id', '') or ""

            # 只处理文本、卡片、富文本消息
            if msg_type not in ("text", "post", "interactive"):
                return

            # 提取消息文本
            text = _extract_text(message.content, msg_type)
            if not text:
                return

            # 检测是否为告警
            if not detector.is_alert(text, sender_id):
                return

            logger.info("检测到告警: chat=%s sender=%s text=%s", chat_id, sender_id, text[:100])

            # 添加"处理中"表情回应 (💪 表示正在处理)
            try:
                from app.lark.card_sender import add_reaction
                asyncio.run_coroutine_threadsafe(
                    add_reaction(message.message_id, "MUSCLE"),
                    main_loop,
                )
            except Exception:
                logger.warning("添加处理中表情失败", exc_info=True)

            # 调度异步工作流到主线程事件循环
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    _trigger_workflow(text, chat_id, message.message_id, sender_id),
                    main_loop,
                )
            else:
                logger.warning("主线程事件循环不可用，跳过工作流触发")

        except Exception:
            logger.exception("处理飞书消息异常")

    return handle_message


def _extract_text(content: str | None, msg_type: str) -> str:
    """从消息内容中提取文本。"""
    if not content:
        return ""
    try:
        data = json.loads(content)
        if msg_type == "text":
            return data.get("text", "")
        if msg_type == "interactive":
            # 卡片消息：提取 title 和所有文本字段
            parts = []
            title = data.get("title", "")
            if isinstance(title, dict):
                title = title.get("content", "")
            if title:
                parts.append(title)
            # 递归提取所有文本
            _extract_card_text(data, parts)
            return "\n".join(parts)
        if msg_type == "post":
            # 富文本：提取所有 text 节点
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


def _extract_card_text(obj: Any, parts: list[str]) -> None:
    """递归提取卡片中的文本。"""
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
    alert_text: str,
    chat_id: str,
    message_id: str,
    sender_id: str,
) -> None:
    """触发 LangGraph 工作流处理告警，并保存完整结果到数据库。"""
    from uuid import uuid4

    from app.graph.workflow import create_workflow

    # 加载环境上下文
    env_context = None
    try:
        from app.db import session_scope
        from app.db.models.environment_context import EnvironmentContext
        from sqlalchemy import select
        async with session_scope() as session:
            stmt = select(EnvironmentContext).where(EnvironmentContext.id == 1)
            result = await session.execute(stmt)
            ctx = result.scalar_one_or_none()
            if ctx and ctx.content.strip():
                env_context = ctx.content
    except Exception:
        logger.warning("加载环境上下文失败", exc_info=True)

    initial_state: GraphState = {
        "incident_id": str(uuid4()),
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
        "env_context": env_context,
        "llm_turns": [],
        "llm_cost_tokens": 0,
        "final_status": None,
    }

    # 无 checkpoint 的简单模式（开发/测试用）
    workflow = create_workflow()
    app = workflow.compile()

    logger.info("启动工作流: incident=%s", initial_state["incident_id"])
    try:
        result = await app.ainvoke(initial_state)
        logger.info(
            "工作流完成: incident=%s status=%s llm_turns=%d",
            result.get("incident_id"),
            result.get("final_status"),
            len(result.get("llm_turns", [])),
        )

        # 保存结果到数据库
        await _save_workflow_result(result)

        # 发送诊断结果到飞书群
        await _send_result_to_chat(chat_id, result)

        # 添加"完成"表情回应
        try:
            from app.lark.card_sender import add_reaction
            await add_reaction(message_id, "DONE")
        except Exception:
            logger.warning("添加完成表情失败", exc_info=True)

    except Exception:
        logger.exception("工作流执行异常: incident=%s", initial_state["incident_id"])
        # 添加失败表情
        try:
            from app.lark.card_sender import add_reaction
            await add_reaction(message_id, "SKULL")
        except Exception:
            pass


async def _send_result_to_chat(chat_id: str, result: GraphState) -> None:
    """发送诊断结果到飞书群。"""
    from app.lark.card_sender import send_result_card, send_text_message

    incident_id = result.get("incident_id", "unknown")
    diagnosis = result.get("diagnosis_summary", "无诊断结果")
    proposals = result.get("proposals", [])
    severity = result.get("severity") or "unknown"
    category = result.get("category") or "unknown"
    confidence = result.get("confidence") or 0
    final_status = result.get("final_status") or "unknown"
    tokens = result.get("llm_cost_tokens") or 0

    # 构建诊断摘要
    diagnosis_text = diagnosis[:800] if diagnosis else "无诊断结果"

    # 构建修复方案文本
    proposal_lines = []
    for i, p in enumerate(proposals[:5]):  # 最多显示 5 个
        risk = p.get("risk_level", "unknown")
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🔴"}.get(risk, "⚪")
        proposal_lines.append(
            f"{i+1}. {risk_icon} **{p.get('plugin_name', '')}**\n"
            f"   {p.get('description', '')[:100]}"
        )
    proposal_text = "\n".join(proposal_lines) if proposal_lines else "无修复方案"

    # 发送卡片
    try:
        card = {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔍 告警诊断完成 - {severity.upper()}",
                },
                "template": {"p0": "red", "p1": "orange", "p2": "yellow", "p3": "green"}.get(severity, "blue"),
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**分类**\n{category}"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**严重程度**\n{severity.upper()}"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**置信度**\n{confidence:.0%}"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**状态**\n{final_status}"}},
                    ],
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**诊断结论**\n{diagnosis_text}"},
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**修复方案**\n{proposal_text}"},
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"incident: {incident_id} | tokens: {tokens}"},
                    ],
                },
            ],
        }

        from app.lark.card_sender import _send_to_chat
        await _send_to_chat(chat_id, "interactive", card)
        logger.info("诊断结果已发送到群: chat=%s incident=%s", chat_id, incident_id)

    except Exception:
        logger.exception("发送诊断结果失败: chat=%s", chat_id)


async def _save_workflow_result(result: GraphState) -> None:
    """保存工作流结果（含 LLM 对话）到数据库。"""
    from sqlalchemy import select

    from app.db import session_scope
    from app.db.models.diagnosis import Diagnosis
    from app.db.models.fix_proposal import FixProposal
    from app.db.models.incident import Incident
    from app.db.models.llm_turn import LLMTurn

    try:
        async with session_scope() as session:
            incident_id = result.get("incident_id")

            # 检查是否已存在
            existing_result = await session.execute(
                select(Incident).where(Incident.id == incident_id)
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.status = result.get("final_status") or existing.status
                existing.category = result.get("category") or existing.category
                existing.service = result.get("service") or existing.service
                existing.severity = result.get("severity") or existing.severity
                existing.summary = (result.get("diagnosis_summary") or existing.summary or "")[:1024]
                existing.llm_cost_tokens = result.get("llm_cost_tokens", 0)
                incident = existing
            else:
                incident = Incident(
                    id=incident_id,
                    fingerprint=result.get("raw_alert", "")[:64],
                    status=result.get("final_status") or "completed",
                    category=result.get("category"),
                    service=result.get("service"),
                    severity=result.get("severity"),
                    summary=(result.get("diagnosis_summary") or "")[:1024],
                    raw_alert={"text": result.get("raw_alert", "")},
                    chat_id=result.get("source_meta", {}).get("chat_id"),
                    source_message_id=result.get("source_meta", {}).get("msg_id"),
                    llm_cost_tokens=result.get("llm_cost_tokens", 0),
                )
                session.add(incident)

            # 保存 Diagnosis
            if result.get("diagnosis_summary"):
                diagnosis = Diagnosis(
                    incident_id=incident.id,
                    root_cause=result["diagnosis_summary"][:2048],
                    confidence=result.get("confidence", 0),
                    evidence=[result.get("evidence", {})],
                )
                session.add(diagnosis)

            # 保存 Proposals
            for p in result.get("proposals", []):
                proposal = FixProposal(
                    incident_id=incident.id,
                    plugin_name=p.get("plugin_name", ""),
                    args=p.get("args", {}),
                    risk_level=p.get("risk_level", "medium"),
                    description=p.get("description", ""),
                    expected_outcome=p.get("expected_outcome"),
                    source=p.get("source", "plugin"),
                )
                session.add(proposal)

            # 保存 LLM 对话轮次
            for t in result.get("llm_turns", []):
                turn = LLMTurn(
                    incident_id=incident.id,
                    phase=t.get("phase", ""),
                    turn_index=t.get("turn_index", 0),
                    role=t.get("role", ""),
                    content=str(t.get("content", ""))[:10000],
                    tool_name=t.get("tool_name"),
                    tool_input=t.get("tool_input"),
                )
                session.add(turn)

            await session.flush()
            logger.info("工作流结果已保存: incident=%s, llm_turns=%d", incident.id, len(result.get("llm_turns", [])))

    except Exception:
        logger.exception("保存工作流结果失败")

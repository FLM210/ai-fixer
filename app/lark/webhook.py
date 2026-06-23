"""飞书 HTTP Webhook 事件接收端点。

支持两种模式:
1. WebSocket (默认): 机器人主动连接飞书
2. HTTP 回调: 飞书推送事件到此端点
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()

# 事件处理器引用 (由 main.py 注入)
_event_handler = None
_card_handler = None


def set_event_handler(handler: Any) -> None:
    """设置事件处理器。"""
    global _event_handler
    _event_handler = handler


def set_card_handler(handler: Any) -> None:
    """设置卡片回调处理器。"""
    global _card_handler
    _card_handler = handler


def _verify_signature(
    token: str, timestamp: str, nonce: str, signature: str, body: str
) -> bool:
    """验证飞书事件签名。"""
    if not token:
        return True  # 未配置 token 则跳过验证

    content = timestamp + nonce + token + body
    computed = hashlib.sha256(content.encode()).hexdigest()
    return computed == signature


@router.post("/lark/event")
async def lark_event(request: Request) -> dict:
    """接收飞书事件回调。"""
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # URL 验证 (飞书配置回调时的握手)
    if body.get("type") == "url_verification":
        logger.info("飞书 URL 验证请求")
        return {"challenge": body.get("challenge", "")}

    # 事件签名验证
    header = body.get("header", {})
    token = header.get("token", "")
    timestamp = header.get("create_time", "")
    nonce = header.get("nonce", "")
    signature = request.headers.get("X-Lark-Signature", "")

    if signature and not _verify_signature(
        token, timestamp, nonce, signature, body_str
    ):
        logger.warning("飞书事件签名验证失败")
        raise HTTPException(status_code=403, detail="Signature verification failed")

    event_type = header.get("event_type", "")
    logger.info("收到飞书事件: type=%s", event_type)

    # 处理消息事件
    if event_type == "im.message.receive_v1":
        event_data = body.get("event", {})
        if _event_handler:
            try:
                from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

                event_obj = P2ImMessageReceiveV1.builder().build()
                if hasattr(event_obj, "event"):
                    event_obj.event = type(
                        "Event",
                        (),
                        {
                            "message": type(
                                "Message",
                                (),
                                {
                                    "chat_id": event_data.get("message", {}).get(
                                        "chat_id", ""
                                    ),
                                    "msg_type": event_data.get("message", {}).get(
                                        "message_type", ""
                                    ),
                                    "content": event_data.get("message", {}).get(
                                        "content", ""
                                    ),
                                    "message_id": event_data.get("message", {}).get(
                                        "message_id", ""
                                    ),
                                },
                            )(),
                            "sender": type(
                                "Sender",
                                (),
                                {
                                    "sender_id": type(
                                        "SenderId",
                                        (),
                                        {
                                            "open_id": event_data.get("sender", {})
                                            .get("sender_id", {})
                                            .get("open_id", ""),
                                            "user_id": event_data.get("sender", {})
                                            .get("sender_id", {})
                                            .get("user_id", ""),
                                        },
                                    )(),
                                },
                            )(),
                        },
                    )()

                _event_handler(event_obj)
            except Exception:
                logger.exception("处理飞书消息事件异常")
        else:
            await _handle_message_event(event_data)

    return {"code": 0}


@router.post("/lark/card/action")
async def lark_card_action(request: Request) -> dict:
    """处理卡片按钮点击回调。

    支持两种审批类型:
    - diagnosis_approval: 诊断确认 (确认后继续制定修复方案)
    - proposal_approval: 修复方案确认 (确认后执行修复)
    """
    body = await request.json()

    # 签名验证
    timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
    nonce = request.headers.get("X-Lark-Request-Nonce", "")
    signature = request.headers.get("X-Lark-Signature", "")

    if signature:
        body_str = json.dumps(body, ensure_ascii=False)
        from app.config import get_settings

        settings = get_settings()
        if not _verify_signature(
            settings.card_signing_key, timestamp, nonce, signature, body_str
        ):
            logger.warning("卡片回调签名验证失败")
            raise HTTPException(
                status_code=403, detail="Signature verification failed"
            )

    # 提取 action 信息
    action = body.get("action", {})
    value = action.get("value", {})
    open_id = body.get("open_id", "")

    action_type = value.get("action", "")
    incident_id = value.get("incident_id", "")
    kind = value.get("kind", "")

    logger.info(
        "卡片回调: action=%s kind=%s incident=%s user=%s",
        action_type,
        kind,
        incident_id,
        open_id,
    )

    if action_type not in ("approve", "reject"):
        return {"toast": {"type": "warning", "content": "未知操作"}}

    asyncio.create_task(_resume_workflow(incident_id, action_type, open_id))

    toast_msg = {
        "approve": "✅ 已确认, 正在继续处理...",
        "reject": "❌ 已拒绝",
    }.get(action_type, "已处理")

    toast_type = "success" if action_type == "approve" else "info"
    return {"toast": {"type": toast_type, "content": toast_msg}}


async def _resume_workflow(incident_id: str, action: str, user_id: str) -> None:
    """恢复被 interrupt 暂停的工作流 (由卡片按钮回调触发)。"""
    from app.lark.card_sender import send_text_message
    from app.lark.workflow_manager import workflow_manager
    from app.lark.workflow_runner import save_workflow_result, send_workflow_result

    run = workflow_manager.get_by_incident(incident_id)
    if not run:
        logger.warning("未找到待恢复的工作流: incident=%s", incident_id)
        return

    chat_id = run.chat_id
    interrupt_type = run.interrupt_type

    logger.info(
        "恢复工作流: incident=%s action=%s type=%s user=%s",
        incident_id,
        action,
        interrupt_type,
        user_id,
    )

    # 通过 resume 将 action 传递给 LangGraph interrupt
    result = await workflow_manager.resume(incident_id, action)

    if result is not None:
        # 工作流已完成, 保存结果并发送
        logger.info("工作流已完成: incident=%s", incident_id)
        await save_workflow_result(result)
        await send_workflow_result(chat_id, result)
    elif action == "reject":
        # reject 后工作流走到了 escalate/resolve (不应再 interrupt)
        # 或 resume 出错, 通知用户
        label = (
            "诊断确认"
            if interrupt_type == "diagnosis_approval"
            else "修复方案"
        )
        await send_text_message(
            chat_id=chat_id,
            text=f"🚫 {label}已拒绝\nincident: {incident_id}",
        )
    else:
        # approve 后工作流再次 interrupt (例如方案确认), 卡片已发送
        logger.info(
            "工作流继续暂停等待下一步确认: incident=%s", incident_id
        )


async def _handle_message_event(event: dict) -> None:
    """处理消息事件: 分析是否为告警, 触发工作流。"""
    try:
        message = event.get("message", {})
        sender = event.get("sender", {})

        chat_id = message.get("chat_id", "")
        msg_type = message.get(
            "message_type", message.get("msg_type", "")
        )
        content = message.get("content", "")
        message_id = message.get("message_id", "")

        sender_id_obj = sender.get("sender_id", {})
        sender_id = sender_id_obj.get("open_id", "") or sender_id_obj.get(
            "user_id", ""
        )

        if msg_type not in ("text", "post", "interactive"):
            return

        text = _extract_text_from_content(content, msg_type)
        if not text:
            return

        from app.config import get_settings
        from app.lark.detector import AlertDetector

        settings = get_settings()
        detector = AlertDetector(alert_bot_ids=settings.alert_bot_ids)

        if not detector.is_alert(text, sender_id):
            return

        logger.info(
            "检测到告警, 触发工作流: chat=%s sender=%s", chat_id, sender_id
        )

        loop = asyncio.get_running_loop()
        loop.create_task(
            _trigger_workflow(text, chat_id, message_id, sender_id)
        )

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
    alert_text: str, chat_id: str, message_id: str, sender_id: str
) -> None:
    """触发 LangGraph 工作流处理告警 (HTTP 回调模式)。"""
    from uuid import uuid4

    from langgraph.types import GraphInterrupt

    from app.graph.workflow import create_workflow
    from app.lark.card_sender import send_text_message
    from app.lark.workflow_manager import workflow_manager
    from app.lark.workflow_runner import (
        build_initial_state,
        create_checkpointer,
        load_env_context,
    )

    env_context = await load_env_context()
    incident_id = str(uuid4())
    thread_id = str(uuid4())

    initial_state = build_initial_state(
        incident_id=incident_id,
        thread_id=thread_id,
        alert_text=alert_text,
        chat_id=chat_id,
        message_id=message_id,
        sender_id=sender_id,
        env_context=env_context,
    )

    logger.info("启动工作流: incident=%s thread=%s", incident_id, thread_id)

    try:
        checkpointer = await create_checkpointer()
        workflow = create_workflow()
        app = workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        result = await app.ainvoke(initial_state, config=config)

        logger.info(
            "工作流完成: incident=%s status=%s",
            incident_id,
            result.get("final_status"),
        )
        from app.lark.workflow_runner import save_workflow_result, send_workflow_result

        await save_workflow_result(result)
        await send_workflow_result(chat_id, result)

    except GraphInterrupt as e:
        interrupt_type = "unknown"
        if e.interrupts:
            interrupt_data = e.interrupts[0].value
            if isinstance(interrupt_data, dict):
                interrupt_type = interrupt_data.get("type", "unknown")

        logger.info(
            "工作流暂停等待用户确认: incident=%s thread=%s type=%s",
            incident_id,
            thread_id,
            interrupt_type,
        )

        workflow_manager.register_pending(
            thread_id=thread_id,
            incident_id=incident_id,
            chat_id=chat_id,
            interrupt_type=interrupt_type,
            app=app,
            config=config,
        )

    except Exception:
        logger.exception("工作流异常: incident=%s", incident_id)
        await send_text_message(
            chat_id=chat_id,
            text=f"❌ 告警处理异常\nincident: {incident_id}",
        )

"""飞书消息事件处理器: 接收群消息, 识别告警, 触发工作流。

使用 LangGraph interrupt/resume 机制实现两步人工确认:
1. 诊断完成后暂停, 发送诊断确认卡片, 等待用户确认
2. 用户确认后制定修复方案, 发送方案确认卡片, 等待用户确认
3. 用户确认后执行修复
"""

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

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(_make_message_handler(detector, main_loop))
        .build()
    )

    return handler


def _make_message_handler(
    detector: AlertDetector,
    main_loop: asyncio.AbstractEventLoop | None = None,
):
    """创建消息接收处理函数 (同步回调, 内部调度异步工作流)。"""

    def handle_message(data: P2ImMessageReceiveV1) -> None:
        try:
            logger.info("收到飞书事件: %s", type(data).__name__)
            event = data.event
            if not event or not event.message:
                return

            message = event.message
            chat_id = message.chat_id
            msg_type = getattr(message, "msg_type", None) or getattr(
                message, "message_type", ""
            )
            sender = event.sender

            sender_id = ""
            if sender:
                sid = getattr(sender, "sender_id", None)
                if sid:
                    sender_id = (
                        getattr(sid, "open_id", "")
                        or getattr(sid, "user_id", "")
                        or ""
                    )
                if not sender_id:
                    sender_id = (
                        getattr(sender, "app_id", "")
                        or getattr(sender, "id", "")
                        or ""
                    )

            if msg_type not in ("text", "post", "interactive"):
                return

            text = _extract_text(message.content, msg_type)
            if not text:
                return

            if not detector.is_alert(text, sender_id):
                return

            logger.info(
                "检测到告警: chat=%s sender=%s text=%s", chat_id, sender_id, text[:100]
            )

            # 添加"处理中"表情回应
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
                logger.warning("主线程事件循环不可用, 跳过工作流触发")

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
    alert_text: str,
    chat_id: str,
    message_id: str,
    sender_id: str,
) -> None:
    """触发 LangGraph 工作流处理告警 (WebSocket 模式)。"""
    from uuid import uuid4

    from langgraph.errors import GraphInterrupt

    from app.graph.workflow import create_workflow
    from app.lark.workflow_manager import workflow_manager
    from app.lark.workflow_runner import (
        build_initial_state,
        create_checkpointer,
        load_env_context,
        save_workflow_result,
        send_workflow_result,
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

    checkpointer = await create_checkpointer()
    workflow = create_workflow()
    app = workflow.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    logger.info("启动工作流: incident=%s thread=%s", incident_id, thread_id)

    try:
        result = await app.ainvoke(initial_state, config=config)

        logger.info(
            "ainvoke returned: keys=%s, has_interrupt=%s",
            list(result.keys()) if isinstance(result, dict) else type(result),
            "__interrupt__" in result if isinstance(result, dict) else False,
        )

        # 检查是否被 interrupt 暂停
        if isinstance(result, dict) and "__interrupt__" in result:
            interrupt_type = "unknown"
            interrupts = result.get("__interrupt__", [])
            if interrupts and hasattr(interrupts[0], "value"):
                interrupt_data = interrupts[0].value
                if isinstance(interrupt_data, dict):
                    interrupt_type = interrupt_data.get("type", "unknown")

            logger.info(
                "工作流暂停等待确认: incident=%s thread=%s type=%s",
                incident_id, thread_id, interrupt_type,
            )

            workflow_manager.register_pending(
                thread_id=thread_id,
                incident_id=incident_id,
                chat_id=chat_id,
                interrupt_type=interrupt_type,
                app=app,
                config=config,
            )
            return

        logger.info(
            "工作流完成: incident=%s status=%s llm_turns=%d",
            incident_id,
            result.get("final_status"),
            len(result.get("llm_turns", [])),
        )

        await save_workflow_result(result)
        await send_workflow_result(chat_id, result)

        try:
            from app.lark.card_sender import add_reaction

            await add_reaction(message_id, "DONE")
        except Exception:
            logger.warning("添加完成表情失败", exc_info=True)

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
        logger.exception("工作流执行异常: incident=%s", incident_id)
        try:
            from app.lark.card_sender import add_reaction

            await add_reaction(message_id, "SKULL")
        except Exception:
            pass

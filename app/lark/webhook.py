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


def _decrypt_event(encrypt_data: str, encrypt_key: str) -> dict | None:
    """解密飞书加密事件。

    飞书加密策略启用时, 事件体通过 AES-256-CBC 加密后放在 encrypt 字段中。
    解密算法: AES key = SHA256(encrypt_key), IV = 密文前 16 字节。
    """
    import base64

    try:
        from Crypto.Cipher import AES

        key = hashlib.sha256(encrypt_key.encode()).digest()
        decoded = base64.b64decode(encrypt_data)
        iv = decoded[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(decoded[16:])
        # 去除 PKCS7 填充
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        logger.warning("解密飞书事件失败", exc_info=True)
        return None


@router.post("/lark/event")
async def lark_event(request: Request) -> dict:
    """接收飞书事件回调。"""
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 处理加密事件（加密策略启用时，事件体在 encrypt 字段中）
    # 必须在 URL 验证之前解密，因为 challenge 请求也是加密的
    from app.config import get_settings

    settings = get_settings()
    encrypt_key = settings.card_signing_key

    if "encrypt" in body and encrypt_key:
        body = _decrypt_event(body["encrypt"], encrypt_key)
        if body is None:
            raise HTTPException(status_code=400, detail="Decrypt failed")

    # URL 验证 (飞书配置回调时的握手，解密后再检查)
    if body.get("type") == "url_verification":
        logger.info("飞书 URL 验证请求")
        return {"challenge": body.get("challenge", "")}

    # 事件签名验证
    header = body.get("header", {})
    token = header.get("token", "")
    timestamp = header.get("create_time", "")
    nonce = header.get("nonce", "")
    signature = request.headers.get("X-Lark-Signature", "")

    if signature and not encrypt_key:
        # 未启用加密策略时用签名验证（加密策略下 AES 已保证安全）
        if not _verify_signature(
            token, timestamp, nonce, signature, body_str
        ):
            logger.warning(
                "飞书事件签名验证失败: ts=%s nonce=%s sig=%s",
                repr(timestamp), repr(nonce), repr(signature[:20]),
            )
            raise HTTPException(status_code=403, detail="Signature verification failed")

    event_type = header.get("event_type", "")
    logger.info("收到飞书事件: type=%s", event_type)

    # 处理消息事件
    if event_type == "im.message.receive_v1":
        event_data = body.get("event", {})
        # 直接使用原始事件数据处理（兼容所有 lark-oapi 版本）
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

    # 处理加密请求（加密策略启用时，请求体在 encrypt 字段中）
    from app.config import get_settings

    settings = get_settings()
    encrypt_key = settings.card_signing_key

    logger.info(
        "卡片回调: body_keys=%s, has_encrypt=%s, encrypt_key=%s",
        list(body.keys()),
        "encrypt" in body,
        "configured" if encrypt_key else "empty",
    )

    if "encrypt" in body and encrypt_key:
        body = _decrypt_event(body["encrypt"], encrypt_key)
        if body is None:
            raise HTTPException(status_code=400, detail="Decrypt failed")

    # URL 验证（飞书配置卡片回调时的握手，解密后再检查）
    if body.get("challenge"):
        return {"challenge": body["challenge"]}

    # 签名验证（加密策略下跳过，AES 已保证安全）
    signature = request.headers.get("X-Lark-Signature", "")
    if signature and not encrypt_key:
        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        body_str = json.dumps(body, ensure_ascii=False)
        if not _verify_signature(
            "", timestamp, nonce, signature, body_str
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
        "卡片回调: action=%s kind=%s incident=%s user=%s body_keys=%s action_keys=%s value=%s",
        action_type,
        kind,
        incident_id,
        open_id,
        list(body.keys()),
        list(action.keys()) if isinstance(action, dict) else type(action),
        repr(value)[:200] if value else "empty",
    )

    if action_type not in ("approve", "reject"):
        # 非操作请求（如事件通知），静默返回不显示 toast
        return {}

    # 添加表情回应表示用户选择
    open_message_id = body.get("open_message_id", "")
    if open_message_id:
        try:
            from app.lark.card_sender import add_reaction

            emoji = "DONE" if action_type == "approve" else "SHAKE"
            await add_reaction(open_message_id, emoji)
        except Exception:
            logger.debug("添加卡片表情回应失败", exc_info=True)

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

    # 优先用 incident_id 匹配，找不到则用 chat_id 匹配最新待确认工作流
    run = workflow_manager.get_by_incident(incident_id)
    if not run:
        logger.info(
            "incident_id 未匹配，尝试 fallback: incident=%s", incident_id
        )
        # 从所有 pending run 中找最新的
        for r in workflow_manager._pending.values():
            run = r
            break
        if not run:
            logger.warning("未找到待恢复的工作流: incident=%s", incident_id)
            return

    chat_id = run.chat_id
    interrupt_type = run.interrupt_type
    thread_id = run.thread_id
    source_message_id = run.source_message_id

    logger.info(
        "恢复工作流: incident=%s action=%s type=%s user=%s",
        incident_id,
        action,
        interrupt_type,
        user_id,
    )

    # 通过 resume 将 action 传递给 LangGraph interrupt
    try:
        result = await workflow_manager.resume_by_thread(thread_id, action)
    except Exception:
        logger.exception("工作流恢复执行异常: incident=%s", incident_id)
        # 给原始告警消息添加失败表情
        if source_message_id:
            try:
                from app.lark.card_sender import add_reaction

                await add_reaction(source_message_id, "SKULL")
            except Exception:
                pass
        await send_text_message(
            chat_id=chat_id,
            text=f"❌ 修复流程异常\nincident: {incident_id}",
        )
        return

    if result is not None:
        # 工作流已完成, 保存结果并发送
        logger.info("工作流已完成: incident=%s", incident_id)
        await save_workflow_result(result)
        await send_workflow_result(chat_id, result)

        # 如果最终状态不是 resolved，给原始消息添加失败表情
        final_status = result.get("final_status", "")
        if final_status and final_status != "resolved" and source_message_id:
            try:
                from app.lark.card_sender import add_reaction

                await add_reaction(source_message_id, "SKULL")
            except Exception:
                pass

    elif action == "reject":
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
        logger.info("_handle_message_event called, event keys=%s", list(event.keys()))
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

        # 收到消息后添加表情回应（确认机器人收到了消息）
        if message_id:
            try:
                from app.lark.card_sender import add_reaction

                await add_reaction(message_id, "MUSCLE")
            except Exception:
                logger.debug("添加表情回应失败", exc_info=True)

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

    from langgraph.errors import GraphInterrupt

    from app.graph.workflow import create_workflow
    from app.lark.card_sender import send_text_message
    from app.lark.workflow_manager import workflow_manager
    from app.lark.workflow_runner import build_initial_state, load_env_context

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
        # 直接创建 MemorySaver，避免任何缓存
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        logger.info("checkpointer id=%s, type=%s", id(checkpointer), type(checkpointer).__name__)

        workflow = create_workflow()
        app = workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        result = await app.ainvoke(initial_state, config=config)

        # ingest_node 会用数据库生成的 UUID 替换 incident_id
        incident_id = result.get("incident_id", incident_id)

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
                source_message_id=message_id,
            )
            return

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
            source_message_id=message_id,
        )

    except Exception:
        logger.exception("工作流异常: incident=%s", incident_id)
        # 给原始告警消息添加失败表情
        if message_id:
            try:
                from app.lark.card_sender import add_reaction

                await add_reaction(message_id, "SKULL")
            except Exception:
                pass
        await send_text_message(
            chat_id=chat_id,
            text=f"❌ 告警处理异常\nincident: {incident_id}",
        )

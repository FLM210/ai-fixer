"""飞书消息和卡片发送工具。"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_tenant_access_token: str | None = None


async def _get_tenant_access_token() -> str:
    """获取 tenant_access_token。"""
    global _tenant_access_token
    if _tenant_access_token:
        return _tenant_access_token

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.lark_app_id,
                "app_secret": settings.lark_app_secret,
            },
            timeout=10,
        )
        data = resp.json()
        _tenant_access_token = data.get("tenant_access_token", "")
        return _tenant_access_token


async def _send_to_chat(chat_id: str, msg_type: str, content: dict) -> bool:
    """发送消息到群聊。"""
    token = await _get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "receive_id": chat_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            timeout=15,
        )
        result = resp.json()
        if result.get("code") != 0:
            logger.error("发送消息失败: %s", result)
            return False
        return True


async def _reply_to_message(message_id: str, msg_type: str, content: dict) -> bool:
    """回复指定消息（在原消息下创建会话线程）。"""
    token = await _get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
            },
            timeout=15,
        )
        result = resp.json()
        if result.get("code") != 0:
            logger.error("回复消息失败: %s", result)
            return False
        return True


async def send_text_message(chat_id: str, text: str) -> bool:
    """发送纯文本消息。"""
    return await _send_to_chat(chat_id, "text", {"text": text})


async def add_reaction(message_id: str, emoji_type: str) -> bool:
    """给消息添加表情回应。

    常用 emoji_type:
    - PROCESSING: 处理中
    - DONE: 完成
    - THUMBSUP: 点赞
    - SMILE: 微笑
    - HEART: 爱心
    """
    token = await _get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reactions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "reaction_type": {
                    "emoji_type": emoji_type,
                },
            },
            timeout=10,
        )
        result = resp.json()
        if result.get("code") != 0:
            logger.error("添加表情失败: %s", result)
            return False
        return True


async def send_result_card(
    chat_id: str,
    incident_id: str,
    diagnosis: str,
    execution_results: list[dict],
    auto_resolved: bool = False,
) -> bool:
    """发送诊断/执行结果卡片。"""
    status_icon = "✅" if auto_resolved else "📊"
    status_text = "已自动修复" if auto_resolved else "分析完成"

    # 构建执行结果文本
    result_lines = []
    for r in execution_results:
        icon = "✅" if r.get("status") == "success" else "❌"
        result_lines.append(
            f"{icon} {r.get('plugin_name', 'unknown')}: {r.get('status', 'unknown')}"
        )

    execution_text = "\n".join(result_lines) if result_lines else "无执行操作"

    card = {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{status_icon} 告警处理结果 - {status_text}",
            },
            "template": "green" if auto_resolved else "blue",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**诊断结论**\n{diagnosis[:500]}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**执行结果**\n{execution_text}",
                },
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"incident: {incident_id}",
                    }
                ],
            },
        ],
    }

    return await _send_to_chat(chat_id, "interactive", card)


async def send_approval_card(
    chat_id: str,
    incident_id: str,
    diagnosis: str,
    confidence: float,
    category: str,
    severity: str,
    proposals: list[dict],
    policy_decisions: list[dict],
) -> bool:
    """发送审批卡片，包含确认/拒绝按钮。"""
    # 构建修复方案文本
    proposal_lines = []
    for i, p in enumerate(proposals):
        risk = p.get("risk_level", "unknown")
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        proposal_lines.append(
            f"{i + 1}. {risk_icon} **{p.get('plugin_name', 'unknown')}**\n"
            f"   {p.get('description', '无描述')}\n"
            f"   风险: {risk}"
        )

    proposal_text = "\n".join(proposal_lines) if proposal_lines else "无修复方案"

    # 构建高风险操作列表
    high_risk_items = []
    for d in policy_decisions:
        if d.get("decision") == "require_approval":
            idx = d.get("proposal_index", 0)
            if idx < len(proposals):
                high_risk_items.append(proposals[idx].get("plugin_name", "unknown"))

    high_risk_text = ", ".join(high_risk_items) if high_risk_items else "无"

    severity_colors = {"p0": "red", "p1": "orange", "p2": "yellow", "p3": "green"}

    card = {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"⚠️ 需要确认 - {severity.upper()} 告警",
            },
            "template": severity_colors.get(severity, "red"),
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**分类**\n{category}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**严重程度**\n{severity.upper()}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**置信度**\n{confidence:.0%}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**需审批操作**\n{high_risk_text}"},
                    },
                ],
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**诊断结论**\n{diagnosis[:500]}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**修复方案**\n{proposal_text}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 批准执行"},
                        "type": "primary",
                        "value": {
                            "action": "approve",
                            "incident_id": incident_id,
                        },
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                        "type": "danger",
                        "value": {
                            "action": "reject",
                            "incident_id": incident_id,
                        },
                    },
                ],
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"incident: {incident_id}",
                    }
                ],
            },
        ],
    }

    return await _send_to_chat(chat_id, "interactive", card)


async def send_diagnosis_confirm_card(
    chat_id: str,
    incident_id: str,
    diagnosis: str,
    confidence: float,
    category: str,
    severity: str,
    service: str,
    evidence: dict[str, object] | None = None,
    source_message_id: str = "",
) -> bool:
    """发送诊断确认卡片，包含确认/拒绝按钮。"""
    from app.lark.cards import CardRenderer

    renderer = CardRenderer()

    # 清理文本中的 JSON 特殊字符
    def _sanitize(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "").replace("\t", " ")

    # 构建证据文本
    evidence_text = ""
    if evidence:
        parts = []
        for key, val in list(evidence.items())[:3]:
            snippet = _sanitize(str(val)[:200])
            parts.append(f"- **{key}**: {snippet}")
        evidence_text = "\\n".join(parts)

    card_json = renderer.render_diagnosis_confirm(
        incident_id=incident_id,
        severity=severity,
        category=category,
        service=service,
        diagnosis=_sanitize(diagnosis[:500]),
        confidence=confidence,
        evidence_text=evidence_text,
        source_message_id=source_message_id,
    )
    card = json.loads(card_json, strict=False)
    if source_message_id:
        return await _reply_to_message(source_message_id, "interactive", card)
    return await _send_to_chat(chat_id, "interactive", card)


async def send_proposal_confirm_card(
    chat_id: str,
    incident_id: str,
    diagnosis: str,
    confidence: float,
    category: str,
    severity: str,
    proposals: list[dict],
    policy_decisions: list[dict] | None = None,
    source_message_id: str = "",
) -> bool:
    """发送修复方案确认卡片，包含确认/拒绝按钮。"""
    from app.lark.cards import CardRenderer

    renderer = CardRenderer()

    # 构建方案文本
    proposal_lines = []
    for i, p in enumerate(proposals):
        risk = p.get("risk_level", "unknown")
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        proposal_lines.append(
            f"{i + 1}. {risk_icon} **{p.get('plugin_name', 'unknown')}**\n"
            f"   {p.get('description', '无描述')}\n"
            f"   风险: {risk}"
        )
    proposal_text = "\n".join(proposal_lines) if proposal_lines else "无修复方案"

    # 构建高风险操作文本
    high_risk_text = ""
    if policy_decisions:
        high_risk_items = []
        for d in policy_decisions:
            if d.get("decision") in ("require_approval", "escalate"):
                idx = d.get("proposal_index", 0)
                if idx < len(proposals):
                    high_risk_items.append(proposals[idx].get("plugin_name", "unknown"))
        if high_risk_items:
            high_risk_text = ", ".join(high_risk_items)

    card_json = renderer.render_proposal_confirm(
        incident_id=incident_id,
        severity=severity,
        category=category,
        diagnosis=diagnosis[:500],
        confidence=confidence,
        proposal_text=proposal_text,
        high_risk_text=high_risk_text,
        source_message_id=source_message_id,
    )
    card = json.loads(card_json, strict=False)
    if source_message_id:
        return await _reply_to_message(source_message_id, "interactive", card)
    return await _send_to_chat(chat_id, "interactive", card)

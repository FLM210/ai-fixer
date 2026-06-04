from __future__ import annotations

import json
from datetime import UTC, datetime

from app.graph.state import GraphState


async def send_card(chat_id: str, card_content: str) -> dict[str, str]:
    """发送飞书卡片消息。Task 10 实现后将替换为 LarkClient.send_message()。"""
    # TODO: 替换为 LarkClient.send_message()
    return {'message_id': 'om_card_placeholder'}


def build_diagnosis_card(state: GraphState) -> str:
    """构建诊断+审批卡片 JSON。Task 12 实现 Jinja2 渲染后将替换。"""
    card = {
        'type': 'template',
        'data': {
            'template_id': 'diagnosis_approval',
            'template_variable': {
                'incident_id': state['incident_id'],
                'severity': state.get('severity', 'unknown'),
                'service': state.get('service', 'unknown'),
                'diagnosis_summary': state.get('diagnosis_summary', ''),
                'confidence': state.get('confidence', 0),
                'proposals': state.get('proposals', []),
            },
        },
    }
    return json.dumps(card)


async def await_approval_node(state: GraphState) -> GraphState:
    card_json = build_diagnosis_card(state)
    chat_id = state['source_meta'].get('chat_id', '')
    await send_card(chat_id, card_json)
    state['awaiting_since'] = datetime.now(UTC)
    return state

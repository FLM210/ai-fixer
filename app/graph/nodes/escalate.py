from __future__ import annotations

from app.graph.state import GraphState


async def send_escalate_card(chat_id: str, incident_id: str, reason: str) -> None:
    """发送升级卡片到飞书群。Task 12 实现 Jinja2 渲染后将替换。"""
    pass


async def escalate_node(state: GraphState) -> GraphState:
    """升级节点: 发送升级卡片,标记事件需要人工介入。"""
    chat_id = state['source_meta'].get('chat_id', '')
    reason = '执行失败' if state.get('execution_results') else '置信度过低'
    await send_escalate_card(chat_id, state['incident_id'], reason)
    state['final_status'] = 'escalated'
    return state

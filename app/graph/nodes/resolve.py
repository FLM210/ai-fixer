from __future__ import annotations

import logging

from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def send_resolve_card(chat_id: str, incident_id: str, summary: str) -> None:
    """发送结案卡片到飞书群。Task 12 实现 Jinja2 渲染后将替换。"""
    pass


async def _store_incident_memory(state: GraphState) -> None:
    """将已解决的 incident 存入向量记忆。如果 memory 模块不可用则静默跳过。"""
    try:
        from app.config import get_settings
        from app.memory import EmbeddingClient, IncidentMemoryStore

        settings = get_settings()
        if not settings.embedding_enabled:
            return

        emb_cfg = settings.embedding
        embedding_client = EmbeddingClient(
            base_url=emb_cfg["base_url"],
            api_key=emb_cfg["api_key"],
            model=emb_cfg["model"],
        )
        store = IncidentMemoryStore(settings.database_url, embedding_client)

        # 提取修复信息
        fixes = []
        for result in state.get('execution_results', []):
            if result.get('status') == 'success':
                fixes.append(result.get('plugin_name', ''))
        fix_applied = ', '.join(fixes) if fixes else None

        # 提取 outcome
        outcomes = []
        for result in state.get('execution_results', []):
            outcomes.append(f"{result.get('plugin_name')}: {result.get('status')}")
        outcome = '; '.join(outcomes) if outcomes else None

        await store.store(
            incident_id=state['incident_id'],
            alert_text=state['raw_alert'],
            category=state.get('category'),
            diagnosis_summary=state.get('diagnosis_summary'),
            fix_applied=fix_applied,
            outcome=outcome,
        )
        logger.info("已存储 incident %s 的向量记忆", state['incident_id'])
    except Exception as e:
        logger.debug("存储 incident 记忆跳过: %s", e)


async def resolve_node(state: GraphState) -> GraphState:
    """结案节点: 发送结案卡片,标记事件已解决,存储记忆。"""
    chat_id = state['source_meta'].get('chat_id', '')
    await send_resolve_card(
        chat_id,
        state['incident_id'],
        state.get('diagnosis_summary') or '已解决',
    )
    state['final_status'] = 'resolved'

    # 存储 incident 记忆
    await _store_incident_memory(state)

    return state

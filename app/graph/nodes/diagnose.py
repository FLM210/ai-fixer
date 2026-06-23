import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState
from app.llm import LLMMessage
from app.llm.factory import build_llm_client
from app.plugins import global_registry
from app.plugins.base import PluginContext, PluginResult

logger = logging.getLogger(__name__)

DIAGNOSE_PROMPT = """你是一个全栈 SRE 工程师，精通容器(K8s/Docker)、数据库(PostgreSQL/MySQL/Redis)、中间件(Nginx/Kafka/RabbitMQ)、网络、云服务(AWS/GCP/Azure)、监控(Prometheus/Grafana/Loki)等。

当前 incident 信息:
- 类别: {category}
- 严重程度: {severity}
- 受影响服务: {service}

{env_context_section}
告警原文:
{alert}
{similar_incidents_section}{knowledge_section}
请使用可用的诊断工具收集证据（shell 命令、K8s API、监控查询等），然后给出根因分析和置信度(0-1)。
"""


async def _search_similar_incidents(state: GraphState) -> list[dict[str, Any]]:
    """搜索历史相似 incident。如果 memory 模块不可用则静默跳过。"""
    try:
        from app.memory import EmbeddingClient, IncidentMemoryStore

        settings = get_settings()
        if not settings.embedding_enabled:
            return []

        emb_cfg = settings.embedding
        embedding_client = EmbeddingClient(
            base_url=emb_cfg["base_url"],
            api_key=emb_cfg["api_key"],
            model=emb_cfg["model"],
        )
        store = IncidentMemoryStore(settings.database_url, embedding_client)
        similar = await store.search(
            alert_text=state["raw_alert"],
            category=state.get("category"),
            limit=3,
            min_similarity=0.7,
        )
        return [
            {
                "incident_id": s.incident_id,
                "alert": s.alert_text,
                "category": s.category,
                "diagnosis": s.diagnosis_summary,
                "fix": s.fix_applied,
                "outcome": s.outcome,
                "similarity": round(s.similarity, 3),
            }
            for s in similar
        ]
    except Exception as e:
        logger.debug("相似 incident 搜索跳过: %s", e)
        return []


def _format_similar_incidents(similar: list[dict[str, Any]]) -> str:
    """将相似 incident 格式化为 LLM context。"""
    if not similar:
        return ""
    lines = ["\n历史相似 incident（仅供参考）:"]
    for i, s in enumerate(similar, 1):
        lines.append(f"  {i}. [{s['category'] or '未知'}] {s['alert'][:100]}")
        if s["diagnosis"]:
            lines.append(f"     诊断: {s['diagnosis'][:150]}")
        if s["fix"]:
            lines.append(f"     修复: {s['fix']}")
        if s["outcome"]:
            lines.append(f"     结果: {s['outcome']}")
        lines.append(f"     相似度: {s['similarity']}")
    lines.append("")
    return "\n".join(lines)


async def _search_knowledge_base(state: GraphState) -> list[dict[str, Any]]:
    """检索知识库中相关的修复手册。如果知识库模块不可用则静默跳过。"""
    try:
        from app.knowledge.search import KnowledgeSearchService
        from app.memory import EmbeddingClient

        settings = get_settings()
        if not settings.embedding_enabled:
            return []

        emb_cfg = settings.embedding
        embedding_client = EmbeddingClient(
            base_url=emb_cfg["base_url"],
            api_key=emb_cfg["api_key"],
            model=emb_cfg["model"],
        )
        search_service = KnowledgeSearchService(settings.database_url, embedding_client)
        results = await search_service.search(
            query=state["raw_alert"],
            category=state.get("category"),
            limit=3,
            min_similarity=0.6,
        )
        return [
            {
                "entry_id": r.entry_id,
                "title": r.title,
                "content": r.content,
                "category": r.category,
                "source_type": r.source_type,
                "similarity": r.similarity,
            }
            for r in results
        ]
    except Exception as e:
        logger.debug("知识库检索跳过: %s", e)
        return []


def _format_knowledge_context(knowledge: list[dict[str, Any]]) -> str:
    """将知识库检索结果格式化为 LLM context。"""
    if not knowledge:
        return ""
    lines = ["\n知识库相关手册（优先参考）:"]
    for i, k in enumerate(knowledge, 1):
        lines.append(f"  {i}. [{k['category'] or '通用'}] {k['title']}")
        # 截取前 200 字符作为摘要
        content_preview = k["content"][:200].replace("\n", " ")
        lines.append(f"     内容: {content_preview}...")
        lines.append(f"     来源: {k['source_type']} | 相似度: {k['similarity']}")
    lines.append("")
    return "\n".join(lines)


# 第一阶段提示词：无工具初步分析
PHASE1_PROMPT = """你是一个全栈 SRE 工程师。请根据以下信息进行初步分析。

当前 incident 信息:
- 类别: {category}
- 严重程度: {severity}
- 受影响服务: {service}

{env_context_section}
告警原文:
{alert}
{similar_incidents_section}{knowledge_section}
请分析：
1. 最可能的根因（1-2 句话）
2. 需要进一步排查的方向（如有）
3. 置信度（0-1，表示你对根因判断的确信程度）

输出格式：
根因: <你的判断>
需要排查: <是/否，如果是，说明需要查什么>
置信度: <0-1>
"""

# 第二阶段提示词：针对性工具排查
PHASE2_PROMPT = """基于初步分析，根因可能是：{preliminary_diagnosis}

请使用工具进行针对性排查，验证或修正上述判断。只调用必要的工具。
"""


def _select_relevant_tools(category: str | None) -> list:
    """根据告警类别选择相关工具，避免给 LLM 太多选择。"""
    all_specs = global_registry.as_tool_specs(category="diagnostic")

    # shell.exec 始终可用
    selected = [s for s in all_specs if s.name == "shell.exec"]

    # 根据类别添加相关工具
    category_lower = (category or "").lower()

    if any(k in category_lower for k in ["k8s", "pod", "container", "node", "deploy"]):
        selected.extend([s for s in all_specs if s.name.startswith("k8s.")])

    if any(k in category_lower for k in ["database", "db", "postgres", "pg", "mysql", "redis"]):
        selected.extend([s for s in all_specs if s.name.startswith("pg.")])

    if any(k in category_lower for k in ["monitor", "metric", "prom", "grafana"]):
        selected.extend([s for s in all_specs if s.name.startswith("prom.")])

    if any(k in category_lower for k in ["log", "loki"]):
        selected.extend([s for s in all_specs if s.name.startswith("loki.")])

    if any(k in category_lower for k in ["sentry", "error", "exception"]):
        selected.extend([s for s in all_specs if s.name.startswith("sentry.")])

    # 如果没有匹配到特定类别，返回 shell + 少量通用工具
    if len(selected) <= 1:
        selected.extend(
            [s for s in all_specs if s.name in ("k8s.list_pods", "prom.query", "loki.query")]
        )

    # 去重并限制数量
    seen = set()
    unique = []
    for s in selected:
        if s.name not in seen:
            seen.add(s.name)
            unique.append(s)

    return unique[:6]  # 最多 6 个工具


def _extract_confidence(text: str) -> float:
    """从 LLM 输出中提取置信度。"""
    import re

    # 提取置信度数值
    match = re.search(r"置信度[：:]\s*([\d.]+)", text)
    if match:
        try:
            return min(float(match.group(1)), 1.0)
        except ValueError:
            pass

    # 如果说"需要排查"，降低置信度
    if re.search(r"需要排查[：:]\s*是", text):
        return 0.4

    # 如果说"不需要排查"或"确定"，提高置信度
    if re.search(r"需要排查[：:]\s*否|不需要排查|确定", text):
        return 0.9

    return 0.5  # 默认


async def run_diagnose_loop(state: GraphState, max_turns: int = 16) -> dict[str, Any]:
    settings = get_settings()
    client = build_llm_client(settings)
    confidence_threshold = settings.diagnose_confidence_threshold

    # 搜索历史相似 incident
    similar = await _search_similar_incidents(state)
    similar_section = _format_similar_incidents(similar)

    # 搜索知识库
    knowledge = await _search_knowledge_base(state)
    knowledge_section = _format_knowledge_context(knowledge)

    env_context = state.get("env_context")
    env_context_section = f"生产环境信息:\n{env_context}\n\n" if env_context else ""

    evidence: dict[str, Any] = {}
    diagnosis_messages: list[dict[str, Any]] = []
    llm_turns: list[dict[str, Any]] = []
    total_tokens = 0

    # ═══════════════════════════════════════════════
    # 第一阶段：无工具初步分析
    # ═══════════════════════════════════════════════
    phase1_prompt = PHASE1_PROMPT.format(
        category=state.get("category", "unknown"),
        severity=state.get("severity", "unknown"),
        service=state.get("service", "unknown"),
        alert=state["raw_alert"],
        similar_incidents_section=similar_section,
        knowledge_section=knowledge_section,
        env_context_section=env_context_section,
    )

    messages = [LLMMessage(role="user", content=phase1_prompt)]
    llm_turns.append(
        {
            "phase": "diagnose",
            "turn_index": 0,
            "role": "user",
            "content": phase1_prompt,
        }
    )

    response = await client.complete(
        system="你是一个全栈 SRE 工程师。根据告警信息和环境上下文进行初步分析，判断根因。",
        messages=messages,
        tools=None,  # 不给工具
    )

    total_tokens += response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
    preliminary_diagnosis = response.text
    confidence = _extract_confidence(preliminary_diagnosis)

    messages.append(LLMMessage(role="assistant", content=preliminary_diagnosis))
    diagnosis_messages.append({"role": "assistant", "content": preliminary_diagnosis})
    llm_turns.append(
        {
            "phase": "diagnose",
            "turn_index": 1,
            "role": "assistant",
            "content": preliminary_diagnosis,
        }
    )

    logger.info("诊断阶段1: 置信度=%.2f, 根因=%s", confidence, preliminary_diagnosis[:100])

    # ═══════════════════════════════════════════════
    # 第二阶段：如果置信度不足，用工具深入排查
    # ═══════════════════════════════════════════════
    if confidence < confidence_threshold:
        # 根据类别选择相关工具
        tools = _select_relevant_tools(state.get("category"))
        tool_names = [t.name for t in tools]
        logger.info("诊断阶段2: 置信度不足，启用工具排查 tools=%s", tool_names)

        # 添加第二阶段提示
        phase2_msg = LLMMessage(
            role="user",
            content=PHASE2_PROMPT.format(
                preliminary_diagnosis=preliminary_diagnosis[:300],
            ),
        )
        messages.append(phase2_msg)
        llm_turns.append(
            {
                "phase": "diagnose",
                "turn_index": 2,
                "role": "user",
                "content": phase2_msg.content,
            }
        )

        # 工具调用循环
        for turn_idx in range(max_turns - 2):
            response = await client.complete(
                system="你是一个全栈 SRE 工程师。使用工具验证初步分析，收集证据。",
                messages=messages,
                tools=tools,
            )

            total_tokens += response.usage.get("input_tokens", 0) + response.usage.get(
                "output_tokens", 0
            )
            messages.append(LLMMessage(role="assistant", content=response.text))
            diagnosis_messages.append({"role": "assistant", "content": response.text})

            llm_turns.append(
                {
                    "phase": "diagnose",
                    "turn_index": turn_idx * 2 + 3,
                    "role": "assistant",
                    "content": response.text,
                }
            )

            if response.stop_reason == "end_turn":
                preliminary_diagnosis = response.text
                break

            # 执行工具调用
            if response.tool_uses:
                tasks = []
                for tu in response.tool_uses:
                    plugin = global_registry.get(tu.name)
                    ctx = PluginContext(
                        incident_id=state["incident_id"],
                        actor="agent",
                        trace_id=state["trace_id"],
                    )
                    tasks.append(plugin.execute(ctx, tu.input))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for tu, result in zip(response.tool_uses, results, strict=False):
                    if isinstance(result, BaseException):
                        tool_output = str(result)
                        tool_result: dict[str, Any] = {"error": str(result)}
                    else:
                        assert isinstance(result, PluginResult)
                        tool_result = result.output
                        tool_output = str(tool_result)
                        evidence.setdefault(tu.name, []).append(tool_result)

                    messages.append(LLMMessage(role="tool", content=tool_output, tool_use_id=tu.id))
                    diagnosis_messages.append(
                        {
                            "role": "tool",
                            "tool_use_id": tu.id,
                            "content": tool_output,
                        }
                    )
                    llm_turns.append(
                        {
                            "phase": "diagnose",
                            "turn_index": turn_idx * 2 + 4,
                            "role": "tool",
                            "content": tool_output,
                            "tool_name": tu.name,
                            "tool_input": tu.input,
                        }
                    )

    return {
        "diagnosis_summary": preliminary_diagnosis,
        "confidence": confidence,
        "evidence": evidence,
        "diagnosis_messages": diagnosis_messages,
        "similar_incidents": similar,
        "llm_turns": llm_turns,
        "total_tokens": total_tokens,
    }


async def diagnose_node(state: GraphState) -> GraphState:
    result = await run_diagnose_loop(state)
    state["diagnosis_summary"] = result["diagnosis_summary"]
    state["confidence"] = result["confidence"]
    state["evidence"] = result["evidence"]
    state["diagnosis_messages"] = result["diagnosis_messages"]
    state["similar_incidents"] = result.get("similar_incidents", [])
    state["llm_cost_tokens"] = state.get("llm_cost_tokens", 0) + result.get("total_tokens", 0)
    # 合并 LLM 对话记录
    state.setdefault("llm_turns", []).extend(result.get("llm_turns", []))
    return state

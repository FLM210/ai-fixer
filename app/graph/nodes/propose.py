import json
import logging
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState, ProposalDraft
from app.llm import LLMMessage
from app.llm.factory import build_llm_client
from app.plugins import global_registry

logger = logging.getLogger(__name__)

PROPOSE_PROMPT = """你是一个全栈 SRE 工程师，负责根据诊断结果制定修复方案。

诊断结果:
{diagnosis_summary}

置信度: {confidence}

{env_context_section}可用修复工具:
{plugin_list}

请根据诊断结果和环境信息,选择合适的修复工具并生成修复建议。
**重要：只选择与当前环境匹配的工具，不要使用与环境不符的工具（例如非 K8s 环境不要使用 k8s 相关工具）。**

输出 JSON 数组:
[
  {{
    "plugin_name": "工具名",
    "args": {{"参数": "值"}},
    "risk_level": "low|medium|high",
    "description": "修复描述",
    "expected_outcome": "预期结果",
    "rollback_hint": "回滚提示(可选)"
  }}
]

如果不需要修复,输出空数组 []。
"""


async def generate_proposals(
    state: GraphState,
) -> tuple[list[ProposalDraft], list[dict[str, Any]], int]:
    settings = get_settings()
    client = build_llm_client(settings)

    # 获取修复插件列表
    plugin_specs = global_registry.list_specs(category="remediation")
    plugin_list = "\n".join(
        [
            f"- {s.name}: {s.description} (风险:{s.risk_level}, 资源:{s.resource_type})"
            + (" [需审批]" if s.requires_approval else "")
            for s in plugin_specs
        ]
    )

    env_context = state.get("env_context")
    env_context_section = f"生产环境信息:\n{env_context}\n\n" if env_context else ""

    prompt = PROPOSE_PROMPT.format(
        diagnosis_summary=state.get("diagnosis_summary", "未知"),
        confidence=state.get("confidence", 0),
        env_context_section=env_context_section,
        plugin_list=plugin_list,
    )
    llm_turns: list[dict[str, Any]] = [
        {"phase": "propose", "turn_index": 0, "role": "user", "content": prompt}
    ]

    response = await client.complete(
        system="你是一个全栈 SRE 工程师，精通容器、数据库、中间件、网络、云服务等。只输出 JSON。",
        messages=[LLMMessage(role="user", content=prompt)],
    )

    total_tokens = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
    llm_turns.append(
        {"phase": "propose", "turn_index": 1, "role": "assistant", "content": response.text}
    )

    try:
        # 从 LLM 响应中提取 JSON（兼容 markdown 代码块等格式）
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        proposals = json.loads(text, strict=False)
        if not isinstance(proposals, list):
            return [], llm_turns, total_tokens
        return (
            [
                ProposalDraft(
                    plugin_name=p["plugin_name"],
                    args=p.get("args", {}),
                    risk_level=p.get("risk_level", "medium"),
                    description=p.get("description", ""),
                    expected_outcome=p.get("expected_outcome"),
                    rollback_hint=p.get("rollback_hint"),
                    source="plugin",
                )
                for p in proposals
            ],
            llm_turns,
            total_tokens,
        )
    except (json.JSONDecodeError, KeyError):
        return [], llm_turns, total_tokens


async def propose_node(state: GraphState) -> GraphState:
    try:
        proposals, turns, tokens = await generate_proposals(state)
    except Exception as e:
        logger.error("生成修复方案失败: %s", e)
        proposals = []
        turns = [{"phase": "propose", "turn_index": 0, "role": "assistant", "content": f"错误: {e}"}]
        tokens = 0
    state["proposals"] = proposals
    state["llm_cost_tokens"] = state.get("llm_cost_tokens", 0) + tokens
    state.setdefault("llm_turns", []).extend(turns)
    return state

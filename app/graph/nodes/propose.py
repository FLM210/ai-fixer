import json
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState, ProposalDraft
from app.llm import LLMMessage
from app.llm.factory import build_llm_client
from app.plugins import global_registry

PROPOSE_PROMPT = """你是一个全栈 SRE 工程师，负责根据诊断结果制定修复方案。

诊断结果:
{diagnosis_summary}

置信度: {confidence}

可用修复工具:
{plugin_list}

请根据诊断结果,选择合适的修复工具并生成修复建议。输出 JSON 数组:
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

    prompt = PROPOSE_PROMPT.format(
        diagnosis_summary=state.get("diagnosis_summary", "未知"),
        confidence=state.get("confidence", 0),
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
        proposals = json.loads(response.text)
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
    proposals, turns, tokens = await generate_proposals(state)
    state["proposals"] = proposals
    state["llm_cost_tokens"] = state.get("llm_cost_tokens", 0) + tokens
    state.setdefault("llm_turns", []).extend(turns)
    return state

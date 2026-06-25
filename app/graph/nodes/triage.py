import json
import logging
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState
from app.llm import LLMMessage
from app.llm.factory import build_llm_client

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """你是一个全栈 SRE 工程师，负责对告警进行分类和严重程度评估。请分析以下告警,输出 JSON:
{{
  "category": "根据告警内容和环境信息判断具体类别（如：容器故障、内存溢出、CPU 过高、磁盘问题、网络异常、数据库问题、中间件问题、应用错误、API 限流等）",
  "severity": "p0|p1|p2|p3",
  "service": "受影响的服务名"
}}

{env_context_section}
告警内容:
{alert}
"""


async def classify_alert(
    alert: str, env_context: str | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    settings = get_settings()
    logger.info("Triage: 开始分类, provider=%s model=%s", settings.llm.provider, settings.llm.model)
    client = build_llm_client(settings)
    turns: list[dict[str, Any]] = []
    total_tokens = 0
    try:
        env_context_section = ""
        if env_context:
            env_context_section = f"生产环境信息:\n{env_context}\n\n"

        prompt = TRIAGE_PROMPT.format(alert=alert, env_context_section=env_context_section)
        turns.append({"role": "user", "content": prompt})

        response = await client.complete(
            system="你是一个全栈 SRE 工程师，精通容器、K8s、数据库、中间件、网络、云服务等。只输出 JSON。",
            messages=[LLMMessage(role="user", content=prompt)],
        )
        turns.append({"role": "assistant", "content": response.text})
        total_tokens = response.usage.get("input_tokens", 0) + response.usage.get(
            "output_tokens", 0
        )

        logger.info("Triage: LLM 响应=%s, tokens=%d", response.text[:200], total_tokens)
        # 从 LLM 响应中提取 JSON（兼容 markdown 代码块等格式）
        text = response.text.strip()
        if text.startswith("```"):
            # 去掉 markdown 代码块
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        result: dict[str, Any] = json.loads(text, strict=False)
        return result, turns, total_tokens
    except Exception as e:
        logger.error("Triage: LLM 调用失败: %s", e)
        turns.append({"role": "assistant", "content": f"错误: {e}"})
        return {"category": "other", "severity": "p2", "service": "unknown"}, turns, total_tokens


async def triage_node(state: GraphState) -> GraphState:
    result, turns, tokens = await classify_alert(state["raw_alert"], state.get("env_context"))
    state["category"] = result.get("category")
    state["severity"] = result.get("severity")
    state["service"] = result.get("service")
    state["llm_cost_tokens"] = state.get("llm_cost_tokens", 0) + tokens
    # 记录 LLM 对话
    for i, t in enumerate(turns):
        state.setdefault("llm_turns", []).append(
            {
                "phase": "triage",
                "turn_index": i,
                "role": t["role"],
                "content": t["content"],
            }
        )
    return state

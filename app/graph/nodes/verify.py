from __future__ import annotations

from app.graph.state import GraphState


async def check_recovery(state: GraphState) -> bool:
    """检查指标/状态是否恢复。

    实际应调用 k8s.describe_pod 或 prom.query 检查指标。
    这里简化: 如果所有执行都成功,认为恢复。
    """
    results = state.get("execution_results", [])
    return all(r["status"] == "success" for r in results)


async def verify_node(state: GraphState) -> GraphState:
    """复查节点: 验证执行结果,确定最终状态。"""
    recovered = await check_recovery(state)
    state["final_status"] = "resolved" if recovered else "failed"
    return state

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, StateGraph

from app.graph.state import GraphState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


def should_continue_after_ingest(state: GraphState) -> str:
    if state.get("is_duplicate"):
        return END
    return "triage"


def should_continue_after_diagnosis_approval(state: GraphState) -> str:
    """诊断确认后决定走向：确认→propose，拒绝→escalate。"""
    if state.get("diagnosis_approved"):
        return "propose"
    return "escalate"


def should_continue_after_propose(state: GraphState) -> str:
    if not state.get("proposals"):
        return "resolve"
    confidence = state.get("confidence")
    if confidence is not None and confidence < 0.3:
        return "escalate"
    return "policy_evaluate"


def should_continue_after_policy(state: GraphState) -> str:
    """根据策略评估结果决定走向。"""
    decisions = state.get("policy_decisions", [])
    if not decisions:
        return "send_proposal_card"

    # 有需要升级的 → 升级
    if any(d["decision"] == "escalate" for d in decisions):
        return "escalate"

    # 全部自动执行 → 自动批准并跳过确认
    if all(d["decision"] == "auto_execute" for d in decisions):
        state["approval_decisions"] = {f"prop-{d['proposal_index']}": "approved" for d in decisions}
        state["proposals_approved"] = True
        return "execute"

    # 部分或全部需审批 → 走确认流程
    return "send_proposal_card"


def should_continue_after_proposal_approval(state: GraphState) -> str:
    """修复方案确认后决定走向：确认→execute，拒绝→escalate。"""
    if state.get("proposals_approved"):
        return "execute"
    return "escalate"


def should_continue_after_execute(state: GraphState) -> str:
    results = state.get("execution_results", [])
    if all(r["status"] == "success" for r in results):
        return "verify"
    if any(r["status"] == "success" for r in results):
        return "propose"
    return "escalate"


def should_continue_after_verify(state: GraphState) -> str:
    # verify 节点会设置 final_status
    if state.get("final_status") == "resolved":
        return "resolve"
    return "escalate"


def create_workflow() -> StateGraph[GraphState]:
    from app.graph.nodes.await_diagnosis_approval import (
        await_diagnosis_approval_node,
        send_diagnosis_card_node,
    )
    from app.graph.nodes.await_proposal_approval import (
        await_proposal_approval_node,
        send_proposal_card_node,
    )
    from app.graph.nodes.diagnose import diagnose_node  # type: ignore[import-untyped]
    from app.graph.nodes.escalate import escalate_node  # type: ignore[import-untyped]
    from app.graph.nodes.execute import execute_node  # type: ignore[import-untyped]
    from app.graph.nodes.ingest import ingest_node  # type: ignore[import-untyped]
    from app.graph.nodes.policy_evaluate import policy_evaluate_node
    from app.graph.nodes.propose import propose_node  # type: ignore[import-untyped]
    from app.graph.nodes.resolve import resolve_node  # type: ignore[import-untyped]
    from app.graph.nodes.triage import triage_node  # type: ignore[import-untyped]
    from app.graph.nodes.verify import verify_node  # type: ignore[import-untyped]

    workflow = StateGraph(GraphState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("send_diagnosis_card", send_diagnosis_card_node)
    workflow.add_node("await_diagnosis_approval", await_diagnosis_approval_node)
    workflow.add_node("propose", propose_node)
    workflow.add_node("policy_evaluate", policy_evaluate_node)
    workflow.add_node("send_proposal_card", send_proposal_card_node)
    workflow.add_node("await_proposal_approval", await_proposal_approval_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("resolve", resolve_node)
    workflow.add_node("escalate", escalate_node)

    workflow.set_entry_point("ingest")

    workflow.add_conditional_edges("ingest", should_continue_after_ingest)
    workflow.add_edge("triage", "diagnose")
    workflow.add_edge("diagnose", "send_diagnosis_card")
    workflow.add_edge("send_diagnosis_card", "await_diagnosis_approval")
    workflow.add_conditional_edges("await_diagnosis_approval", should_continue_after_diagnosis_approval)
    workflow.add_conditional_edges("propose", should_continue_after_propose)
    workflow.add_conditional_edges("policy_evaluate", should_continue_after_policy)
    workflow.add_edge("send_proposal_card", "await_proposal_approval")
    workflow.add_conditional_edges("await_proposal_approval", should_continue_after_proposal_approval)
    workflow.add_conditional_edges("execute", should_continue_after_execute)
    workflow.add_conditional_edges("verify", should_continue_after_verify)
    workflow.add_edge("resolve", END)
    workflow.add_edge("escalate", END)

    return workflow


async def create_app(checkpoint_url: str) -> CompiledStateGraph[GraphState, Any]:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    pool = AsyncConnectionPool(checkpoint_url, kwargs={"row_factory": dict_row})
    checkpointer = AsyncPostgresSaver(conn=pool)  # type: ignore[arg-type]
    await checkpointer.setup()
    workflow = create_workflow()
    return workflow.compile(checkpointer=checkpointer)

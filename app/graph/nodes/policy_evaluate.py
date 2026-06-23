"""策略评估节点：对每个 proposal 进行风险评估，决定自动执行/需审批/升级。"""

from __future__ import annotations

from app.config import get_settings
from app.engine.policy import ExecutionPolicy, PolicyContext
from app.graph.state import GraphState, PolicyDecision
from app.plugins import global_registry

_policy: ExecutionPolicy | None = None


def _get_policy() -> ExecutionPolicy:
    global _policy
    if _policy is None:
        _policy = ExecutionPolicy(get_settings().safety_fences)
    return _policy


async def policy_evaluate_node(state: GraphState) -> GraphState:
    policy = _get_policy()
    decisions: list[PolicyDecision] = []

    for i, proposal in enumerate(state.get("proposals", [])):
        plugin_name = proposal.get("plugin_name", "")
        plugin_spec = (
            global_registry.get(plugin_name).spec if global_registry.has(plugin_name) else None
        )

        ctx = PolicyContext(
            incident_id=state["incident_id"],
            category=state.get("category"),
            severity=state.get("severity"),
            namespace=proposal.get("args", {}).get("namespace"),
            plugin_name=plugin_name,
            plugin_risk_level=proposal.get(
                "risk_level", plugin_spec.risk_level if plugin_spec else "medium"
            ),
            plugin_requires_approval=plugin_spec.requires_approval if plugin_spec else False,
            proposal_args=proposal.get("args", {}),
        )

        decision = policy.evaluate(ctx)
        decisions.append(
            PolicyDecision(
                proposal_index=i,
                decision=decision.value,
                reason=f"risk={ctx.plugin_risk_level}, ns={ctx.namespace}",
            )
        )

    state["policy_decisions"] = decisions
    return state

"""执行策略引擎测试。"""

from app.config.settings import SafetyFences
from app.engine.policy import ExecutionDecision, ExecutionPolicy, PolicyContext


def make_policy(**overrides) -> ExecutionPolicy:
    fences = SafetyFences(**overrides)
    return ExecutionPolicy(fences)


def test_low_risk_auto_execute():
    policy = make_policy()
    ctx = PolicyContext(
        incident_id="inc-1",
        plugin_name="k8s.restart_pod",
        plugin_risk_level="low",
        proposal_args={"namespace": "default", "pod_name": "x"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.AUTO_EXECUTE


def test_medium_risk_auto_execute_in_whitelist():
    policy = make_policy()
    ctx = PolicyContext(
        incident_id="inc-2",
        plugin_name="k8s.restart_pod",
        plugin_risk_level="medium",
        proposal_args={"namespace": "default"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.AUTO_EXECUTE


def test_high_risk_requires_approval():
    policy = make_policy()
    ctx = PolicyContext(
        incident_id="inc-3",
        plugin_name="k8s.rollback_deployment",
        plugin_risk_level="high",
        proposal_args={"namespace": "default"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL


def test_critical_risk_escalates():
    policy = make_policy()
    ctx = PolicyContext(
        incident_id="inc-4",
        plugin_name="k8s.rollback_deployment",
        plugin_risk_level="critical",
        proposal_args={"namespace": "default"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.ESCALATE


def test_namespace_outside_fence_requires_approval():
    policy = make_policy(auto_namespaces=["staging"])
    ctx = PolicyContext(
        incident_id="inc-5",
        plugin_name="k8s.restart_pod",
        plugin_risk_level="low",
        proposal_args={"namespace": "production"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL


def test_approval_verb_requires_approval():
    policy = make_policy(require_approval_verbs=["delete", "drain"])
    ctx = PolicyContext(
        incident_id="inc-6",
        plugin_name="k8s.delete_evicted_pods",
        plugin_risk_level="low",
        proposal_args={"namespace": "default", "verb": "delete"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL


def test_plugin_requires_approval_flag():
    policy = make_policy()
    ctx = PolicyContext(
        incident_id="inc-7",
        plugin_name="llm.kubectl_action",
        plugin_risk_level="low",
        plugin_requires_approval=True,
        proposal_args={"namespace": "default"},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL


def test_quota_exceeded_requires_approval():
    policy = make_policy(max_auto_fixes_per_hour=2)
    ctx = PolicyContext(
        incident_id="inc-8",
        plugin_name="k8s.restart_pod",
        plugin_risk_level="low",
        proposal_args={"namespace": "default"},
    )
    # 前两次通过
    assert policy.evaluate(ctx) == ExecutionDecision.AUTO_EXECUTE
    assert policy.evaluate(ctx) == ExecutionDecision.AUTO_EXECUTE
    # 第三次超配额
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL


def test_large_replica_change_requires_approval():
    policy = make_policy(max_replica_change=5)
    ctx = PolicyContext(
        incident_id="inc-9",
        plugin_name="k8s.scale_deployment",
        plugin_risk_level="medium",
        proposal_args={"namespace": "default", "replicas": 100},
    )
    assert policy.evaluate(ctx) == ExecutionDecision.REQUIRE_APPROVAL

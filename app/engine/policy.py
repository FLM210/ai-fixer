"""执行策略引擎：根据操作风险等级和安全围栏决定执行方式。"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.config.settings import SafetyFences


class ExecutionDecision(StrEnum):
    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"


@dataclass
class PolicyContext:
    """策略评估所需的 incident 上下文。"""
    incident_id: str
    category: str | None = None
    severity: str | None = None
    namespace: str | None = None
    plugin_name: str = ""
    plugin_risk_level: str = "medium"
    plugin_requires_approval: bool = False
    proposal_args: dict[str, Any] = field(default_factory=dict)


class ExecutionPolicy:
    """根据操作风险等级和安全围栏决定执行策略。

    决策逻辑：
    1. critical 风险 → 始终升级
    2. plugin.requires_approval=True → 始终需审批
    3. low 风险 + 在围栏内 → 自动执行
    4. medium 风险 + 在围栏内 + 配额充足 → 自动执行
    5. 其他 → 需审批
    """

    def __init__(self, fences: SafetyFences) -> None:
        self._fences = fences
        self._hourly_counts: dict[str, list[float]] = defaultdict(list)

    def evaluate(self, ctx: PolicyContext) -> ExecutionDecision:
        # critical 始终升级
        if ctx.plugin_risk_level == "critical":
            return ExecutionDecision.ESCALATE

        # 插件标记为始终需审批
        if ctx.plugin_requires_approval:
            return ExecutionDecision.REQUIRE_APPROVAL

        # 检查是否在安全围栏内
        if not self._within_fences(ctx):
            return ExecutionDecision.REQUIRE_APPROVAL

        # 检查配额
        if not self._check_quota(ctx.incident_id):
            return ExecutionDecision.REQUIRE_APPROVAL

        # 风险等级决策
        if ctx.plugin_risk_level == "low":
            return ExecutionDecision.AUTO_EXECUTE
        if ctx.plugin_risk_level == "medium":
            return ExecutionDecision.AUTO_EXECUTE

        # high 风险需审批
        return ExecutionDecision.REQUIRE_APPROVAL

    def _within_fences(self, ctx: PolicyContext) -> bool:
        """检查操作是否在安全围栏内。"""
        fences = self._fences

        # 检查命名空间白名单
        ns = ctx.proposal_args.get("namespace", "")
        if ns and ns not in fences.auto_namespaces:
            return False

        # 检查副本数变更幅度
        scale_to = ctx.proposal_args.get("replicas")
        if isinstance(scale_to, int):
            # 无法直接判断变更幅度，标记需审批
            if abs(scale_to) > fences.max_replica_change:
                return False

        # 检查需要审批的 verb
        verb = ctx.proposal_args.get("verb", "")
        if verb and verb in fences.require_approval_verbs:
            return False

        return True

    def _check_quota(self, incident_id: str) -> bool:
        """检查每小时自动修复配额。"""
        now = time.time()
        cutoff = now - 3600

        # 清理过期记录
        self._hourly_counts[incident_id] = [
            t for t in self._hourly_counts[incident_id] if t > cutoff
        ]

        if len(self._hourly_counts[incident_id]) >= self._fences.max_auto_fixes_per_hour:
            return False

        self._hourly_counts[incident_id].append(now)
        return True

    def record_auto_fix(self, incident_id: str) -> None:
        """记录一次自动修复（供外部调用）。"""
        self._hourly_counts[incident_id].append(time.time())

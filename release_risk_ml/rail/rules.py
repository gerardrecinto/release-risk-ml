"""Deterministic rule layer. Same rules gate inference and filter training data,
so the model only ever sees the cases the rules can't already resolve.
"""

from dataclasses import dataclass

from release_risk_ml.schemas import DeployFeatures


@dataclass
class RuleResult:
    matched: bool
    rule_name: str | None
    high_risk: bool | None  # None when no rule matched (falls through to model)


def evaluate_rules(features: DeployFeatures) -> RuleResult:
    if features.test_pass_rate < 0.8:
        return RuleResult(True, "low_test_pass_rate", high_risk=True)

    if features.is_hotfix and features.code_review_approvals == 0:
        return RuleResult(True, "unreviewed_hotfix", high_risk=True)

    if features.change_failure_history_30d >= 3:
        return RuleResult(True, "repeat_offender_service", high_risk=True)

    if (
        features.test_pass_rate == 1.0
        and features.code_review_approvals >= 2
        and features.lines_changed < 50
        and features.change_failure_history_30d == 0
        and not features.is_hotfix
    ):
        return RuleResult(True, "small_reviewed_clean_history", high_risk=False)

    return RuleResult(False, None, None)

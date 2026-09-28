from release_risk_ml.rail.rules import evaluate_rules
from release_risk_ml.schemas import DeployFeatures, ServiceCriticality


def make_features(**overrides) -> DeployFeatures:
    defaults = dict(
        lines_changed=100,
        files_changed=5,
        test_pass_rate=0.95,
        code_review_approvals=1,
        is_hotfix=False,
        deploy_hour_utc=14,
        time_since_last_deploy_hours=48.0,
        author_past_rollback_rate=0.1,
        change_failure_history_30d=0,
        service_criticality=ServiceCriticality.medium,
    )
    defaults.update(overrides)
    return DeployFeatures(**defaults)


def test_low_test_pass_rate_is_high_risk():
    result = evaluate_rules(make_features(test_pass_rate=0.5))
    assert result.matched
    assert result.rule_name == "low_test_pass_rate"
    assert result.high_risk is True


def test_unreviewed_hotfix_is_high_risk():
    result = evaluate_rules(make_features(is_hotfix=True, code_review_approvals=0))
    assert result.matched
    assert result.rule_name == "unreviewed_hotfix"
    assert result.high_risk is True


def test_repeat_offender_service_is_high_risk():
    result = evaluate_rules(make_features(change_failure_history_30d=5))
    assert result.matched
    assert result.rule_name == "repeat_offender_service"
    assert result.high_risk is True


def test_small_reviewed_clean_history_is_low_risk():
    result = evaluate_rules(
        make_features(
            test_pass_rate=1.0,
            code_review_approvals=2,
            lines_changed=10,
            change_failure_history_30d=0,
            is_hotfix=False,
        )
    )
    assert result.matched
    assert result.rule_name == "small_reviewed_clean_history"
    assert result.high_risk is False


def test_ambiguous_case_falls_through_to_model():
    result = evaluate_rules(
        make_features(
            test_pass_rate=0.9,
            code_review_approvals=1,
            lines_changed=300,
            change_failure_history_30d=1,
            is_hotfix=False,
        )
    )
    assert not result.matched
    assert result.rule_name is None
    assert result.high_risk is None

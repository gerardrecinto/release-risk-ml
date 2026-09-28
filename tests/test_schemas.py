import pytest
from pydantic import ValidationError

from release_risk_ml.schemas import DeployFeatures, ServiceCriticality


def test_valid_features_construct():
    features = DeployFeatures(
        lines_changed=10,
        files_changed=2,
        test_pass_rate=1.0,
        code_review_approvals=1,
        is_hotfix=False,
        deploy_hour_utc=12,
        time_since_last_deploy_hours=10.0,
        author_past_rollback_rate=0.0,
        change_failure_history_30d=0,
        service_criticality=ServiceCriticality.low,
    )
    assert features.service_criticality == "low"


@pytest.mark.parametrize(
    "field,value",
    [
        ("test_pass_rate", 1.5),
        ("test_pass_rate", -0.1),
        ("lines_changed", -1),
        ("deploy_hour_utc", 24),
        ("author_past_rollback_rate", 2.0),
    ],
)
def test_out_of_range_values_rejected(field, value):
    payload = dict(
        lines_changed=10,
        files_changed=2,
        test_pass_rate=1.0,
        code_review_approvals=1,
        is_hotfix=False,
        deploy_hour_utc=12,
        time_since_last_deploy_hours=10.0,
        author_past_rollback_rate=0.0,
        change_failure_history_30d=0,
        service_criticality=ServiceCriticality.low,
    )
    payload[field] = value
    with pytest.raises(ValidationError):
        DeployFeatures(**payload)


def test_invalid_criticality_rejected():
    with pytest.raises(ValidationError):
        DeployFeatures(
            lines_changed=10,
            files_changed=2,
            test_pass_rate=1.0,
            code_review_approvals=1,
            is_hotfix=False,
            deploy_hour_utc=12,
            time_since_last_deploy_hours=10.0,
            author_past_rollback_rate=0.0,
            change_failure_history_30d=0,
            service_criticality="catastrophic",
        )

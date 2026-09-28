import pytest
from fastapi.testclient import TestClient

from release_risk_ml.training.generate_data import generate
from release_risk_ml.training.train import train


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("integration")
    data_path = tmp_dir / "releases.csv"
    generate(n_rows=2000, seed=42).to_csv(data_path, index=False)
    model_dir = tmp_dir / "artifacts"
    train(data_path, model_dir)

    import os

    os.environ["MODEL_DIR"] = str(model_dir)

    from release_risk_ml.serving.app import app

    return TestClient(app)


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_rule_resolved_high_risk(client):
    payload = {
        "lines_changed": 500,
        "files_changed": 10,
        "test_pass_rate": 0.5,
        "code_review_approvals": 2,
        "is_hotfix": False,
        "deploy_hour_utc": 14,
        "time_since_last_deploy_hours": 48.0,
        "author_past_rollback_rate": 0.1,
        "change_failure_history_30d": 0,
        "service_criticality": "low",
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["decision_source"] == "rule"
    assert body["rule_name"] == "low_test_pass_rate"
    assert body["high_risk"] is True


def test_predict_rule_resolved_low_risk(client):
    payload = {
        "lines_changed": 10,
        "files_changed": 2,
        "test_pass_rate": 1.0,
        "code_review_approvals": 2,
        "is_hotfix": False,
        "deploy_hour_utc": 14,
        "time_since_last_deploy_hours": 48.0,
        "author_past_rollback_rate": 0.1,
        "change_failure_history_30d": 0,
        "service_criticality": "low",
    }
    response = client.post("/predict", json=payload)
    body = response.json()
    assert body["decision_source"] == "rule"
    assert body["high_risk"] is False


def test_predict_ambiguous_case_uses_model(client):
    payload = {
        "lines_changed": 300,
        "files_changed": 4,
        "test_pass_rate": 0.9,
        "code_review_approvals": 1,
        "is_hotfix": False,
        "deploy_hour_utc": 14,
        "time_since_last_deploy_hours": 20.0,
        "author_past_rollback_rate": 0.3,
        "change_failure_history_30d": 1,
        "service_criticality": "medium",
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["decision_source"] == "model"
    assert body["risk_score"] is not None
    assert body["model_version"] is not None


def test_predict_rejects_invalid_input(client):
    payload = {"lines_changed": -1}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

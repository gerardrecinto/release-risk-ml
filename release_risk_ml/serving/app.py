"""Local inference service. Run with:

    uvicorn release_risk_ml.serving.app:app --port 8000

No AWS credentials are required for this path. release_risk_ml/serving/README.md
in the repo root documents how this maps onto a SageMaker real-time endpoint.
"""

import os

from fastapi import FastAPI, HTTPException

from release_risk_ml.rail.rules import evaluate_rules
from release_risk_ml.schemas import DeployFeatures, RiskDecision
from release_risk_ml.serving.model_loader import get_cached_model

MODEL_DIR = os.environ.get("MODEL_DIR", "artifacts")
MODEL_RISK_THRESHOLD = float(os.environ.get("MODEL_RISK_THRESHOLD", "0.5"))

app = FastAPI(title="release-risk-ml")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=RiskDecision)
def predict(features: DeployFeatures) -> RiskDecision:
    rule_result = evaluate_rules(features)
    if rule_result.matched:
        return RiskDecision(
            decision_source="rule",
            rule_name=rule_result.rule_name,
            high_risk=rule_result.high_risk,
        )

    try:
        model = get_cached_model(MODEL_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    row = features.model_dump()
    risk_score = model.predict_proba(row)
    return RiskDecision(
        decision_source="model",
        risk_score=round(risk_score, 4),
        high_risk=risk_score >= MODEL_RISK_THRESHOLD,
        model_version=model.model_version,
    )

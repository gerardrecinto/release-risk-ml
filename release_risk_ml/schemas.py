"""Shared input/output validation, used by training, serving, and tests alike."""

from enum import Enum

from pydantic import BaseModel, Field


class ServiceCriticality(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DeployFeatures(BaseModel):
    lines_changed: int = Field(ge=0, le=200_000)
    files_changed: int = Field(ge=0, le=5_000)
    test_pass_rate: float = Field(ge=0.0, le=1.0)
    code_review_approvals: int = Field(ge=0, le=20)
    is_hotfix: bool
    deploy_hour_utc: int = Field(ge=0, le=23)
    time_since_last_deploy_hours: float = Field(ge=0.0, le=24 * 365)
    author_past_rollback_rate: float = Field(ge=0.0, le=1.0)
    change_failure_history_30d: int = Field(ge=0, le=1000)
    service_criticality: ServiceCriticality


class RiskDecision(BaseModel):
    model_config = {"protected_namespaces": ()}

    decision_source: str  # "rule" | "model"
    rule_name: str | None = None
    risk_score: float | None = None  # only populated when decision_source == "model"
    high_risk: bool
    model_version: str | None = None

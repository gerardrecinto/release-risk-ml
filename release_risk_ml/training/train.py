"""Local, reproducible training entry point.

Trains only on the subset of rows the RAIL rule layer would NOT resolve on its
own. Training on the full dataset (including rule-resolved rows) would teach
the model an easy shortcut it will never actually see in production, since
those rows never reach it after the rule gate. Run:

    python -m release_risk_ml.training.train --data data/releases.csv --model-dir artifacts

Mirrors release_risk_ml/training/sagemaker_entry_point.py, which is the same
logic adapted to SageMaker's training-job contract (SM_CHANNEL_TRAIN,
SM_MODEL_DIR).
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from release_risk_ml.rail.rules import evaluate_rules
from release_risk_ml.schemas import DeployFeatures

FEATURE_COLUMNS = [
    "lines_changed",
    "files_changed",
    "test_pass_rate",
    "code_review_approvals",
    "is_hotfix",
    "deploy_hour_utc",
    "time_since_last_deploy_hours",
    "author_past_rollback_rate",
    "change_failure_history_30d",
    "service_criticality",
]
LABEL_COLUMN = "rollback_within_24h"
SEED = 42


def filter_to_ambiguous(df: pd.DataFrame) -> pd.DataFrame:
    keep_mask = []
    for _, row in df.iterrows():
        features = DeployFeatures(
            lines_changed=int(row["lines_changed"]),
            files_changed=int(row["files_changed"]),
            test_pass_rate=float(row["test_pass_rate"]),
            code_review_approvals=int(row["code_review_approvals"]),
            is_hotfix=bool(row["is_hotfix"]),
            deploy_hour_utc=int(row["deploy_hour_utc"]),
            time_since_last_deploy_hours=float(row["time_since_last_deploy_hours"]),
            author_past_rollback_rate=float(row["author_past_rollback_rate"]),
            change_failure_history_30d=int(row["change_failure_history_30d"]),
            service_criticality=row["service_criticality"],
        )
        result = evaluate_rules(features)
        keep_mask.append(not result.matched)
    return df[pd.Series(keep_mask, index=df.index)]


def build_pipeline() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=10,
        random_state=SEED,
        class_weight="balanced",
    )


def train(data_path: Path, model_dir: Path) -> dict:
    df = pd.read_csv(data_path)
    ambiguous_df = filter_to_ambiguous(df)

    encoded = pd.get_dummies(ambiguous_df[FEATURE_COLUMNS], columns=["service_criticality"])
    x_train, x_test, y_train, y_test = train_test_split(
        encoded,
        ambiguous_df[LABEL_COLUMN],
        test_size=0.2,
        random_state=SEED,
        stratify=ambiguous_df[LABEL_COLUMN],
    )

    model = build_pipeline()
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)[:, 1]
    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
        "n_total_rows": len(df),
        "n_ambiguous_rows_used_for_training": len(ambiguous_df),
        "n_rule_resolved_rows_excluded": len(df) - len(ambiguous_df),
        "test_set_size": len(x_test),
    }

    model_dir.mkdir(parents=True, exist_ok=True)
    data_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()[:12]
    model_version = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{data_hash}"

    model_path = model_dir / f"model-{model_version}.joblib"
    joblib.dump({"model": model, "feature_columns": list(encoded.columns)}, model_path)

    baseline_stats = {
        col: {"mean": float(encoded[col].mean()), "std": float(encoded[col].std())}
        for col in encoded.columns
    }

    metadata = {
        "model_version": model_version,
        "model_path": str(model_path),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_data_path": str(data_path),
        "training_data_sha256": data_hash,
        "feature_columns": list(encoded.columns),
        "metrics_observed_on_held_out_test_set": metrics,
        "baseline_feature_stats": baseline_stats,
        "seed": SEED,
    }
    metadata_path = model_dir / f"metadata-{model_version}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    latest_pointer = model_dir / "latest.json"
    latest_pointer.write_text(json.dumps({"model_version": model_version, "metadata_path": str(metadata_path)}, indent=2))

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/releases.csv"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    metadata = train(args.data, args.model_dir)
    print(json.dumps(metadata["metrics_observed_on_held_out_test_set"], indent=2))
    print(f"model_version: {metadata['model_version']}")


if __name__ == "__main__":
    main()

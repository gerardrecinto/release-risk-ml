"""Data-quality and drift checks for incoming inference traffic.

Not wired to a live traffic stream in this portfolio (no deployed endpoint
producing real request logs) — these functions are unit-tested directly
against synthetic before/after batches. In production this would run on a
CloudWatch/SageMaker Model Monitor schedule; see infra/sagemaker.tf.
"""

import numpy as np
import pandas as pd


def population_stability_index(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """PSI < 0.1: no significant shift. 0.1-0.25: moderate. > 0.25: significant drift."""
    breakpoints = np.quantile(baseline, np.linspace(0, 1, bins + 1))
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf

    baseline_counts, _ = np.histogram(baseline, bins=breakpoints)
    current_counts, _ = np.histogram(current, bins=breakpoints)

    baseline_pct = np.clip(baseline_counts / len(baseline), 1e-6, None)
    current_pct = np.clip(current_counts / len(current), 1e-6, None)

    return float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))


def data_quality_report(batch: pd.DataFrame, required_columns: list[str]) -> dict:
    missing_columns = [col for col in required_columns if col not in batch.columns]
    null_rates = {col: float(batch[col].isna().mean()) for col in batch.columns if col in required_columns}
    return {
        "row_count": len(batch),
        "missing_columns": missing_columns,
        "null_rates": null_rates,
        "has_missing_columns": len(missing_columns) > 0,
        "max_null_rate": max(null_rates.values()) if null_rates else 0.0,
    }

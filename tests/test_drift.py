import math

import numpy as np
import pandas as pd

from release_risk_ml.monitoring.drift import data_quality_report, population_stability_index


def test_psi_near_zero_for_identical_distributions():
    rng = np.random.default_rng(1)
    baseline = rng.normal(0, 1, 5000)
    current = rng.normal(0, 1, 5000)
    assert population_stability_index(baseline, current) < 0.05


def test_psi_high_for_shifted_distribution():
    rng = np.random.default_rng(1)
    baseline = rng.normal(0, 1, 5000)
    shifted = rng.normal(3, 1, 5000)
    assert population_stability_index(baseline, shifted) > 0.25


def test_data_quality_report_flags_missing_column():
    batch = pd.DataFrame({"a": [1, 2, 3]})
    report = data_quality_report(batch, required_columns=["a", "b"])
    assert report["has_missing_columns"] is True
    assert "b" in report["missing_columns"]


def test_data_quality_report_flags_nulls():
    batch = pd.DataFrame({"a": [1, None, 3]})
    report = data_quality_report(batch, required_columns=["a"])
    assert math.isclose(report["null_rates"]["a"], 1 / 3, rel_tol=1e-9)

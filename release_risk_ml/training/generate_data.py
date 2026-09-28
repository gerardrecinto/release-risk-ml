"""Synthetic release-event generator.

No real production telemetry exists for this portfolio project, so this module
generates a labeled dataset from a hand-specified risk function plus noise.
The function encodes realistic-looking correlations (unreviewed hotfixes,
low test pass rates, off-hours deploys) but the numbers are synthetic, not
observed. Fixed seed makes the dataset reproducible byte-for-byte.
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

CRITICALITY_WEIGHT = {"low": 0.0, "medium": 0.3, "high": 0.8}

COLUMNS = [
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
    "rollback_within_24h",
]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate(n_rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    files_changed = rng.integers(1, 40, size=n_rows)
    lines_changed = (files_changed * rng.gamma(shape=2.0, scale=15.0, size=n_rows)).astype(int)
    test_pass_rate = np.clip(rng.beta(a=8, b=1.2, size=n_rows), 0.0, 1.0)
    code_review_approvals = rng.integers(0, 4, size=n_rows)
    is_hotfix = rng.random(n_rows) < 0.15
    deploy_hour_utc = rng.integers(0, 24, size=n_rows)
    time_since_last_deploy_hours = rng.exponential(scale=48.0, size=n_rows)
    author_past_rollback_rate = np.clip(rng.beta(a=1.5, b=8, size=n_rows), 0.0, 1.0)
    change_failure_history_30d = rng.poisson(lam=0.6, size=n_rows)
    service_criticality = rng.choice(["low", "medium", "high"], size=n_rows, p=[0.5, 0.35, 0.15])

    criticality_w = np.array([CRITICALITY_WEIGHT[c] for c in service_criticality])
    off_hours = ((deploy_hour_utc < 6) | (deploy_hour_utc > 20)).astype(float)

    risk_logit = (
        -3.0
        + 4.0 * (1.0 - test_pass_rate)
        + 0.015 * (lines_changed / (files_changed + 1))
        + 1.5 * is_hotfix.astype(float)
        - 0.3 * code_review_approvals
        + 2.0 * author_past_rollback_rate
        + 0.5 * change_failure_history_30d
        - 0.01 * np.minimum(time_since_last_deploy_hours, 200)
        + criticality_w
        + 0.4 * off_hours
    )
    probability = np.clip(_sigmoid(risk_logit) + rng.normal(0, 0.05, size=n_rows), 0.0, 1.0)
    rollback_within_24h = rng.binomial(1, probability).astype(bool)

    df = pd.DataFrame(
        {
            "lines_changed": lines_changed,
            "files_changed": files_changed,
            "test_pass_rate": test_pass_rate,
            "code_review_approvals": code_review_approvals,
            "is_hotfix": is_hotfix,
            "deploy_hour_utc": deploy_hour_utc,
            "time_since_last_deploy_hours": time_since_last_deploy_hours,
            "author_past_rollback_rate": author_past_rollback_rate,
            "change_failure_history_30d": change_failure_history_30d,
            "service_criticality": service_criticality,
            "rollback_within_24h": rollback_within_24h,
        }
    )
    return df[COLUMNS]


def sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/releases.csv"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df = generate(args.n_rows, args.seed)
    df.to_csv(args.out, index=False)
    print(f"wrote {len(df)} rows to {args.out}")
    print(f"sha256: {sha256_of_file(args.out)}")
    print(f"base rate rollback_within_24h: {df['rollback_within_24h'].mean():.4f}")


if __name__ == "__main__":
    main()

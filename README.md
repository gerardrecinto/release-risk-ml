# release-risk-ml

A portfolio project demonstrating a RAIL-designed (Rules Applied Instantly,
model only for what's Left) ML operationalization pipeline: deterministic
rules resolve the obvious cases, a trained model only ever sees the
ambiguous ones, and the whole thing is built to map onto AWS SageMaker for
production deployment.

**What it predicts**: given metadata about a proposed deployment (lines
changed, test pass rate, review approvals, deploy time, service history),
whether it's likely to need a rollback within 24 hours.

**Honesty note**: I have no prior professional SageMaker experience. This
project is independently built to demonstrate hands-on model-operationalization
capability — training, registry mapping, deployment topology, monitoring,
and rollback — not a claim of prior production SageMaker usage. The training
data is synthetic (see `release_risk_ml/training/generate_data.py`); metrics
below are observed on that synthetic data, not production numbers.

## Why rules-first

The same rule engine (`release_risk_ml/rail/rules.py`) does two jobs: it
filters which rows the model trains on, and it gates which requests ever
reach the model at inference time. A deploy with a 50% test pass rate
doesn't need a model to tell you it's risky — a rule resolves it in
microseconds with a human-auditable reason. The model is reserved for the
cases where reasonable engineers would actually disagree, which is also
where a wrong rule would do the most damage if you tried to hand-write one.

See `release_risk_ml/rail/rules.py` for the four rules currently
implemented, and `docs/ARCHITECTURE.md` for the full request path.

## Local quickstart (no AWS credentials required)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m release_risk_ml.training.generate_data --n-rows 5000 --seed 42
python -m release_risk_ml.training.train --data data/releases.csv --model-dir artifacts

uvicorn release_risk_ml.serving.app:app --port 8000
# in another shell:
scripts/smoke_test.sh http://localhost:8000
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

## Observed results (synthetic data, this repo, this seed)

Running `python -m release_risk_ml.training.train --data data/releases.csv --model-dir artifacts`
on the 5,000-row synthetic dataset generated with `--seed 42`:

| Metric | Value |
|---|---|
| Rows total | 5,000 |
| Rows resolved by rules (excluded from training) | 1,365 (27.3%) |
| Rows used to train the model (ambiguous only) | 3,635 |
| Held-out test accuracy | 0.7373 |
| Held-out test precision | 0.2485 |
| Held-out test recall | 0.3962 |
| Held-out test ROC-AUC | 0.6981 |

Precision/recall are modest because the ambiguous subset is, by
construction, the hard part of the distribution — the rules already
removed the easy 27%. This is expected and the honest number; a
production version would tune the decision threshold against a real cost
model for false positives vs. false negatives rather than the default 0.5
used here (`MODEL_RISK_THRESHOLD` env var).

Re-run `python -m release_risk_ml.training.train` yourself to reproduce
these numbers — the training data hash is stable for `--seed 42`, so the
result should match exactly, modulo `RandomForestClassifier` internals
between scikit-learn versions.

## When a rule should run before the model

A rule belongs ahead of the model when:
- the decision is legally/operationally non-negotiable regardless of
  context (e.g., an unreviewed hotfix should never be treated as
  low-risk, no matter what a model thinks),
- the case is common enough that resolving it deterministically measurably
  cuts model inference volume and cost, or
- an auditor needs a plain-English reason (`rule_name`), not a probability.

Everything else — where features interact in ways that are real but not
worth hand-coding — goes to the model. See `docs/ARCHITECTURE.md` for the
tradeoffs section.

## Mapping to SageMaker

| Local (this repo) | Production (SageMaker) |
|---|---|
| `release_risk_ml/training/train.py` | Same logic in `sagemaker_entry_point.py`, run as a SageMaker training job (`SKLearn` estimator) |
| `artifacts/model-*.joblib` + `metadata-*.json` | Model registered in SageMaker Model Registry, `model.tar.gz` in S3 |
| `uvicorn ... serving/app.py` | SageMaker real-time endpoint behind `infra/sagemaker.tf` |
| `MODEL_RISK_THRESHOLD` env var | SageMaker endpoint invocation + threshold applied in the calling service |
| `release_risk_ml/monitoring/drift.py` (PSI, null-rate checks) | SageMaker Model Monitor data-quality schedule (`infra/sagemaker.tf`) |
| Canary rollout | Two `production_variants` blocks on one endpoint config, weighted traffic split |

None of the AWS side has been deployed for this portfolio (no AWS account
costs incurred) — `infra/sagemaker.tf` is reference IaC, checked with
`terraform validate` but not `terraform apply`'d. See `docs/COST_NOTES.md`.

## Repo layout

```
release_risk_ml/
  schemas.py            pydantic input/output contracts
  rail/rules.py         deterministic rule layer (shared by training + serving)
  training/
    generate_data.py    synthetic dataset generator (reproducible, seeded)
    train.py            local training entry point
    sagemaker_entry_point.py   same logic, SageMaker training-job contract
  serving/
    app.py               FastAPI inference service
    model_loader.py       loads latest versioned model artifact
  monitoring/drift.py    PSI + data-quality checks
infra/sagemaker.tf       reference IaC: model, endpoint, canary, CloudWatch alarms
tests/                    unit + integration tests (pytest)
scripts/smoke_test.sh     black-box smoke test against a running instance
docs/                     architecture, rollback, cost, security, monitoring, troubleshooting, portfolio summary
```

## Docs

- `docs/ARCHITECTURE.md` — request path, diagram, tradeoffs
- `docs/ROLLBACK.md` — rollback procedure
- `docs/MONITORING.md` — what's monitored and how
- `docs/COST_NOTES.md` — cost-conscious design decisions
- `docs/SECURITY.md` — security notes
- `docs/TROUBLESHOOTING.md` — troubleshooting guide
- `docs/PORTFOLIO_SUMMARY.md` — interview talking points and resume bullets

# Monitoring

## What's actually running today (Observed)

- `tests/test_drift.py` exercises `release_risk_ml/monitoring/drift.py`
  (`population_stability_index`, `data_quality_report`) against synthetic
  before/after batches. These functions work and are unit-tested; they are
  not wired to any live traffic stream, because no live endpoint exists.
- `release_risk_ml/training/train.py` writes `baseline_feature_stats`
  (mean/std per encoded feature) into each `metadata-*.json` at train
  time. This is the baseline a drift check would compare incoming batches
  against.

## What's designed but not deployed (Proposed)

| Signal | Local equivalent | Production mechanism |
|---|---|---|
| Latency | n/a (FastAPI has no built-in histogram wired up here) | CloudWatch `ModelLatency` metric + `high_latency` alarm (`infra/sagemaker.tf`) |
| Errors | HTTP 4xx/5xx from FastAPI, unlogged beyond default uvicorn access log | CloudWatch `Invocation4XXErrors`/`Invocation5XXErrors` + `high_error_rate` alarm |
| Data quality | `data_quality_report()` — callable, unit-tested, not scheduled | SageMaker Model Monitor data-quality schedule (`aws_sagemaker_monitoring_schedule` in `infra/sagemaker.tf` — incomplete, see note below) |
| Feature drift | `population_stability_index()` — callable, unit-tested, not scheduled | Same Model Monitor schedule, PSI or KS-test on live vs. baseline features |

**Gap, stated plainly**: `aws_sagemaker_monitoring_schedule` in
`infra/sagemaker.tf` references a `monitoring_job_definition_name` that
isn't defined as its own resource in this repo. A real deployment needs an
`aws_sagemaker_data_quality_job_definition` (or equivalent) pointing at an
S3 baseline and a monitoring container image. Left as a named gap rather
than a resource that looks complete but silently wouldn't `apply`.

## Adding a metrics endpoint (next slice, not done)

FastAPI has no `/metrics` endpoint in this version. The obvious next step
is `prometheus-fastapi-instrumentator` or a manual middleware timing each
request and exporting histogram buckets for `decision_source=rule` vs.
`decision_source=model` separately — latency profiles for the two paths
should differ by roughly the cost of `model.predict_proba`, and conflating
them would hide a regression in either path. Not implemented; noted as
the natural extension point in `serving/app.py`.

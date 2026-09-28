# Rollback procedure

This describes the rollback path for the SageMaker endpoint topology in
`infra/sagemaker.tf`. It has not been exercised against a real endpoint
(no AWS deployment exists for this portfolio) — it is the documented
procedure for how the two-variant canary setup is designed to be operated,
carried over from the pattern used in production K8s rollbacks (see the
Qualcomm MTTR story: `progressDeadlineSeconds` detection + `kubectl
rollout undo`), adapted to SageMaker's variant-weight primitive instead of
a K8s deployment.

## Canary rollout stages

1. Train and register a new model version (`train.py` / SageMaker training
   job → registry).
2. Deploy it as the `canary` variant at low weight
   (`canary_weight_percent`, default 10%) alongside the existing `current`
   variant at 90%.
3. Watch the CloudWatch alarms in `infra/sagemaker.tf`
   (`high_latency`, `high_error_rate`) scoped to the canary variant name
   for a soak period.
4. **Promote**: flip `canary_weight_percent` toward 100, or swap
   `current`/`canary` model assignments and reapply — no endpoint
   recreation, since both variants live behind the same
   `aws_sagemaker_endpoint`.
5. **Roll back**: set `canary_weight_percent` back to 0. Traffic returns
   to the known-good `current` variant immediately; the bad canary variant
   can be deleted or investigated at leisure since it's no longer serving
   traffic.

## What should trigger an automatic rollback (proposed, not implemented)

- `high_error_rate` alarm fires on the canary variant specifically.
- `high_latency` alarm fires on the canary variant specifically.
- Data-quality monitor (`release_risk_ml/monitoring/drift.py` logic,
  running as a SageMaker Model Monitor schedule) reports
  `has_missing_columns: true` or a null rate above a fixed threshold on
  canary traffic.

None of these are wired to an actual automated weight flip in this
portfolio — that would require a Lambda or Step Functions workflow
subscribed to the CloudWatch alarms, which is a reasonable next slice but
is marked **Proposed**, not built, here.

## Local rollback (serving/app.py)

There is no canary concept in the local FastAPI service — it always loads
whatever `artifacts/latest.json` points to
(`release_risk_ml/serving/model_loader.py`). "Rollback" locally means
re-pointing `latest.json` at an older `metadata-*.json` and restarting the
process; the model cache is process-lifetime (`lru_cache(maxsize=1)`), so
a running process won't pick up the change without a restart. This is a
known gap relative to the production hot-swap behavior a real endpoint
gives you for free — noted, not silently glossed over.

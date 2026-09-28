# Cost notes

No AWS resources have been provisioned for this project — everything in
`infra/sagemaker.tf` is unapplied reference IaC. The notes below describe
the cost-conscious decisions baked into that design, not observed AWS
billing.

## Design decisions and their cost rationale

- **`ml.m5.large` over GPU instances.** The model is a `RandomForestClassifier`
  over ~10 tabular features — no GPU benefit. Real-time endpoints bill by
  instance-hour regardless of utilization, so instance size is the primary
  lever; `ml.m5.large` is the smallest general-purpose instance that comfortably
  serves a model this size.
- **Two variants at partial weight, not two full-size fleets.** The canary
  variant in `infra/sagemaker.tf` runs 1 instance vs. 2 for `current` —
  canary traffic is a small percentage, so it doesn't need equal capacity.
- **RAIL rule gate cuts model invocation volume before it happens.** In the
  observed synthetic run, 27.3% of requests never reach the model (README
  "Observed results" table). On a real SageMaker real-time endpoint, which
  bills per instance-hour rather than per-invocation, this doesn't reduce
  endpoint cost directly — but it does reduce the instance count needed to
  hit a given latency SLA, since ~27% less traffic hits the model. For a
  serverless inference endpoint (billed per invocation + duration) the
  savings would be direct.
- **CloudWatch alarms, not a custom monitoring stack.** `infra/sagemaker.tf`
  uses native `AWS/SageMaker` metrics (`ModelLatency`, `Invocation5XXErrors`)
  rather than standing up a separate observability pipeline — avoids
  running additional compute just to monitor the compute that matters.

## What would cost money if applied

- 3 total `ml.m5.large` instances running continuously (2 current + 1 canary)
- SageMaker Model Monitor scheduled jobs (hourly, per `infra/sagemaker.tf`'s
  cron expression), each a short-lived processing job billed by duration
- CloudWatch alarm evaluations (negligible, but non-zero)
- S3 storage for model artifacts and monitor baseline/output data

None of these have been incurred. If this were applied, the two biggest
levers to cut cost further would be: (1) switching the endpoint to
serverless inference if traffic is bursty/low-volume rather than steady,
and (2) reducing Model Monitor schedule frequency from hourly to daily
once the model is stable.

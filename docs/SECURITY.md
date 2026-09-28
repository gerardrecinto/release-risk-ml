# Security notes

## What's implemented

- **Input validation at the boundary.** Every request to `/predict` is
  parsed through `release_risk_ml.schemas.DeployFeatures` before touching
  rules or the model — out-of-range or malformed input is rejected with a
  422 before any business logic runs (`tests/test_schemas.py`,
  `tests/test_serving_integration.py::test_predict_rejects_invalid_input`).
- **No secrets in source control.** The service takes no credentials —
  it's a local model-serving process with no external calls. `MODEL_DIR`
  and `MODEL_RISK_THRESHOLD` are the only environment-driven config, and
  neither is sensitive.

## Proposed for a real AWS deployment (not implemented here)

- **Least-privilege IAM for the SageMaker execution role.** The role in
  `infra/sagemaker.tf` (`sagemaker_execution_role_arn`) is passed in as a
  variable rather than created here, deliberately — this repo doesn't
  define the IAM policy attached to it. A real deployment should scope
  that role to exactly: read access to the specific S3 prefix holding
  training data, write access to the specific prefix for model artifacts,
  and the ECR pull permission for the training/inference image. Not
  `AmazonSageMakerFullAccess`.
- **Endpoint access control.** `aws_sagemaker_endpoint` in this repo has no
  VPC config or resource policy attached. Production should place the
  endpoint in a VPC with a private subnet and restrict invocation to
  specific IAM principals or a private API Gateway in front of it, not
  expose `InvokeEndpoint` broadly.
- **Encryption at rest for model artifacts.** S3 bucket holding
  `model_artifact_s3_uri` should use SSE-KMS, not default SSE-S3, if the
  training data contains anything sensitive. This project's training data
  is synthetic, so it doesn't matter here — flagged as a general rule for
  reuse.

## Audit logging

`RiskDecision` responses include `decision_source` and, for rule-resolved
cases, `rule_name` — every decision is traceable to either a named rule or
a model version (`model_version` field), which is a deliberate audit
property, not an incidental one. Neither field ever contains a fragment of
the raw model or a customer identifier — this service takes no
personally identifying fields as input in the first place
(`schemas.DeployFeatures` is entirely pipeline metadata).

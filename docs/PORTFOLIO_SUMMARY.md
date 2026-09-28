# Portfolio summary

## What this is

An independently built portfolio project demonstrating a rules-first
(RAIL) approach to ML operationalization: deterministic rules resolve
obvious cases, a trained model handles only the ambiguous remainder, and
the pipeline is designed to map onto AWS SageMaker for training, registry,
deployment, and monitoring. Built to close a real gap — no prior
professional SageMaker or model-operationalization experience — not to
misrepresent one.

## Resume bullets (accurate language only)

- Built a rules-first ML operationalization pipeline (RAIL design) where
  deterministic rules resolve 27% of cases before a model is invoked,
  reducing unnecessary model calls and keeping high-stakes decisions
  auditable to a named rule rather than an opaque score.
- Implemented reproducible model training with content-hashed data
  versioning, timestamped model artifacts, and per-version baseline
  statistics for downstream drift detection.
- Designed a SageMaker deployment topology (Terraform) supporting
  weighted canary rollout and CloudWatch-based latency/error alarming,
  mapped from a working local FastAPI inference service.
- Demonstrated model-operationalization judgment carried over from prior
  CI/CD and Kubernetes rollout work (progressive rollout, automated
  detection, rollback-without-redeploy) applied to a new domain, ML
  serving, rather than claiming prior ML production ownership.

**Not used, and why**: "operated in production," "deployed to AWS,"
"reduced [metric] by [X]%" — none of these are true for this project. No
AWS resources were provisioned; all metrics are Observed against
synthetic data, labeled as such throughout `README.md`.

## Interview talking points

**"Walk me through this project."**
Start with the rules-first framing: most systems that bolt ML onto a
decision pipeline send everything to the model, which is expensive and
makes the easy 90% of cases as unauditable as the hard 10%. This project
inverts that — a small rule engine (`rail/rules.py`) handles the clear
cases in microseconds with a named reason, and the model only sees what's
actually ambiguous, both at training time and at inference time, using the
exact same rule function so the two never drift apart.

**"What would you have done differently with more time?"**
Wire the CloudWatch alarms to an actual automated rollback (currently a
documented manual procedure — `docs/ROLLBACK.md` says as much), and
replace the fixed 0.5 decision threshold with one tuned against a real
cost model for false positives vs. false negatives, rather than a
default.

**"How do you know the model is actually adding value over just more
rules?"**
Honestly: on this synthetic dataset, precision is 0.25 and recall is 0.40
on the ambiguous subset (README table) — modest, because the rules already
removed the easy cases. The right comparison isn't "model vs. no model,"
it's "model vs. an engineer hand-writing five more rules to cover the
ambiguous 73%," which doesn't scale the same way and doesn't produce a
calibrated score. That tradeoff, not a headline accuracy number, is the
actual argument for the model.

**"Have you run this in production?"**
No — stated directly. This is a portfolio project built to demonstrate
the operational pattern (training → registry → deployment → monitoring →
rollback) hands-on, using a synthetic dataset and a local serving path
that runs without AWS credentials. The SageMaker mapping (`infra/sagemaker.tf`,
README's mapping table) documents how it would deploy, but nothing has
been applied against a real AWS account.

## Claims this project supports

- Hands-on experience building a rules-first ML serving architecture
- Reproducible training with artifact versioning
- Working local inference service with input/output validation
- SageMaker-shaped IaC (endpoint, canary variants, CloudWatch alarms),
  validated as HCL, not applied
- A documented (not automated) rollback procedure
- Unit + integration test coverage for rules, schema validation, training,
  and the serving path (24 tests, all passing — see README)

## Claims this project does NOT support (say so directly if asked)

- Prior professional SageMaker usage
- Any production deployment or real user traffic
- Automated rollback (documented procedure only, not wired to alarms)
- Real-world model performance (metrics are on synthetic data only)

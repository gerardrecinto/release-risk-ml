# Troubleshooting

## `FileNotFoundError: No trained model found at artifacts/latest.json`

The FastAPI service returns this as a 503 from `/predict` when it needs
the model (i.e., the rule layer didn't resolve the request) but no model
has been trained yet. Fix:

```bash
python -m release_risk_ml.training.generate_data --n-rows 5000 --seed 42
python -m release_risk_ml.training.train --data data/releases.csv --model-dir artifacts
```

## `scikit-learn` fails to install / tries to compile from source

This happened during development on this machine: the default `python3`
was 3.14, which has no prebuilt scikit-learn wheel yet, so `pip` fell back
to a source build that needs a working C compiler. On this machine, the
`cc` command was shell-aliased to an unrelated tool
(`~/.claude/hooks/cc-launch.sh`), which made the failure confusing —
the actual Xcode `cc` at `/usr/bin/cc` was fine. Fix: use a Python version
with prebuilt wheels (this repo is built and tested against **3.12**):

```bash
python3.12 -m venv .venv
```

If you don't have a shell alias shadowing `cc` and still hit a compiler
error, check `type cc` before assuming Xcode Command Line Tools are
missing.

## `terraform validate` times out: "failed to instantiate provider ... timeout while waiting for plugin to start"

On the machine this was built on, `terraform init` resolved the AWS
provider as `darwin_amd64` (x86_64) even though the machine is arm64 —
`file $(which terraform)` showed the installed `terraform` binary itself
is x86_64, so it picked a matching provider to run under Rosetta.
Running the ~800MB provider binary directly
(`.terraform/providers/.../terraform-provider-aws_v6.66.0_x5`) starts and
initializes fine in isolation (confirmed: prints "Creating Terraform AWS
Provider..." and exits 0), so the binary itself isn't broken. `terraform
validate` still timed out waiting for the plugin handshake in this
sandboxed shell environment specifically — most likely the sandbox's
process/pipe handling interferes with go-plugin's RPC handshake over
stdout, not a translation-speed issue. The HCL in `infra/sagemaker.tf`
was reviewed by hand instead; it has not been machine-validated with
`terraform validate` in this environment. Re-run it yourself in a normal
(non-sandboxed) shell, ideally with an arm64-native `terraform` install,
before trusting it further.

## Pydantic warning: `Field "model_version" ... conflict with protected namespace "model_"`

Fixed in `schemas.py` via `model_config = {"protected_namespaces": ()}`
on `RiskDecision`. `model_version` is a legitimate field name for this
domain (it means "version of the trained model," not "config for a
pydantic model") — the namespace collision is a pydantic v2 convention
that doesn't apply to this usage.

## Model predictions look identical to rule decisions in tests

Check `decision_source` in the response before comparing `high_risk` —
a rule-resolved response has `risk_score: null` and `model_version: null`
by design (see `schemas.RiskDecision`); only `decision_source == "model"`
responses populate those fields.

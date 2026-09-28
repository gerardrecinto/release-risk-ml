# Architecture

## Request path

```
                     POST /predict
                          |
                          v
              +--------------------------+
              |  pydantic validation      |  reject malformed input (422)
              |  (schemas.DeployFeatures) |  before it reaches rules or model
              +--------------------------+
                          |
                          v
              +--------------------------+
              |  RAIL rule layer          |  release_risk_ml/rail/rules.py
              |  (deterministic, <1ms)    |  same rules used to filter
              +--------------------------+  training data
                     |            |
              matched|            |not matched
                     v            v
          +-------------+   +----------------------+
          | return       |   | load cached model    |
          | rule_name +  |   | (joblib, versioned)  |
          | high_risk    |   +----------------------+
          | (no model    |              |
          |  call)       |              v
          +-------------+   +----------------------+
                             | predict_proba         |
                             | risk_score + threshold|
                             | model_version tagged   |
                             +----------------------+
```

## Why this shape

The rule layer and the model share one thing: the set of features. They
don't share a probability space, which is deliberate — a rule's output is
`(matched: bool, high_risk: bool | None)`, not a score. Mixing rule
confidence into the same numeric scale as model confidence is a common
source of silent bugs (a rule that's "80% confident" reads like a
probability but isn't calibrated like one).

## Training/serving symmetry

`filter_to_ambiguous()` in `training/train.py` and the rule gate in
`serving/app.py` both call `evaluate_rules()`. If they diverged (e.g., the
serving path used a newer rules module than what the model was trained
against), the model would start seeing rule-resolved rows in production
that it never saw in training — a subtle but real skew bug. Keeping both
call sites pointed at the same function is the whole mitigation; there's
no additional check beyond that because none is needed while there's only
one rules module.

## Tradeoffs

**Rule ordering matters and is unenforced.** `evaluate_rules()` checks
rules in a fixed sequence and returns on first match. `low_test_pass_rate`
is checked before `unreviewed_hotfix`, so a hotfix with a 50% pass rate
reports as `low_test_pass_rate`, not `unreviewed_hotfix`, even though both
apply. For an audit trail this is acceptable (both reasons say "high
risk"), but it would be wrong if two rules disagreed on the verdict. None
currently do, but that's a property of the current four rules, not
something the code enforces.

**Model excludes rule-resolved rows, which shrinks and reshapes the
training set.** 27.3% of the synthetic dataset is rule-resolved (see
README's Observed Results table) and never reaches the model, in training
or production. This is correct for matching production distribution but
means the model's headline accuracy looks worse in isolation than a
model trained on the full dataset would — that's expected, not a bug: the
easy 27% already left through the rules.

**Threshold is a single global constant.** `MODEL_RISK_THRESHOLD`
(default 0.5) applies uniformly regardless of `service_criticality`. A
real system would likely want a lower bar (more sensitive) for high
criticality services. Not implemented here — noted as a gap, not
hand-waved.

**Local inference caches one model in memory
(`serving/model_loader.py::get_cached_model`, `lru_cache(maxsize=1)`).**
Deploying a new model version requires restarting the process (or,
in production, deploying a new endpoint variant — see `docs/ROLLBACK.md`).
There is no in-process hot-reload.

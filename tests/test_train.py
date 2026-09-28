import json

from release_risk_ml.training.generate_data import generate
from release_risk_ml.training.train import train


def test_generate_is_deterministic_for_fixed_seed():
    df_a = generate(n_rows=200, seed=7)
    df_b = generate(n_rows=200, seed=7)
    assert df_a.equals(df_b)


def test_generate_different_seeds_differ():
    df_a = generate(n_rows=200, seed=7)
    df_b = generate(n_rows=200, seed=8)
    assert not df_a.equals(df_b)


def test_train_produces_artifact_and_metadata(tmp_path):
    data_path = tmp_path / "releases.csv"
    generate(n_rows=2000, seed=42).to_csv(data_path, index=False)

    model_dir = tmp_path / "artifacts"
    metadata = train(data_path, model_dir)

    assert (model_dir / "latest.json").exists()
    assert (model_dir / f"model-{metadata['model_version']}.joblib").exists()

    latest = json.loads((model_dir / "latest.json").read_text())
    assert latest["model_version"] == metadata["model_version"]

    metrics = metadata["metrics_observed_on_held_out_test_set"]
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert metrics["n_rule_resolved_rows_excluded"] > 0
    assert metrics["n_ambiguous_rows_used_for_training"] < metrics["n_total_rows"]

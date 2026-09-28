import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd


class LoadedModel:
    def __init__(self, model, feature_columns: list[str], model_version: str):
        self.model = model
        self.feature_columns = feature_columns
        self.model_version = model_version

    def predict_proba(self, row: dict) -> float:
        encoded = pd.get_dummies(pd.DataFrame([row]))
        encoded = encoded.reindex(columns=self.feature_columns, fill_value=0)
        return float(self.model.predict_proba(encoded)[0, 1])


def load_latest_model(model_dir: Path) -> LoadedModel:
    latest_pointer = model_dir / "latest.json"
    if not latest_pointer.exists():
        raise FileNotFoundError(
            f"No trained model found at {latest_pointer}. Run "
            "`python -m release_risk_ml.training.train` first."
        )
    pointer = json.loads(latest_pointer.read_text())
    metadata = json.loads(Path(pointer["metadata_path"]).read_text())
    bundle = joblib.load(metadata["model_path"])
    return LoadedModel(
        model=bundle["model"],
        feature_columns=bundle["feature_columns"],
        model_version=metadata["model_version"],
    )


@lru_cache(maxsize=1)
def get_cached_model(model_dir_str: str) -> LoadedModel:
    return load_latest_model(Path(model_dir_str))

"""SageMaker training-job entry point.

Same training logic as train.py, adapted to the SageMaker training-job
contract: input channels and the model directory arrive as environment
variables rather than CLI flags. This is the script you'd hand to a
SageMaker Estimator, e.g.:

    from sagemaker.sklearn import SKLearn

    estimator = SKLearn(
        entry_point="release_risk_ml/training/sagemaker_entry_point.py",
        source_dir=".",
        role=sagemaker_execution_role_arn,
        instance_type="ml.m5.large",
        framework_version="1.2-1",
        py_version="py3",
        hyperparameters={"n_estimators": 200, "max_depth": 6},
    )
    estimator.fit({"train": s3_uri_to_releases_csv})

This has not been run against real AWS in this portfolio (no SageMaker
execution role or S3 bucket provisioned) — it is included to show the
production entry point the local train.py maps onto, not a verified run.
"""

import argparse
import os
from pathlib import Path

from release_risk_ml.training.train import train


def main() -> None:
    parser = argparse.ArgumentParser()
    # SageMaker injects these as env vars; the defaults let this run locally too.
    parser.add_argument("--train-channel", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "data"))
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "artifacts"))
    parser.add_argument("--train-file", type=str, default="releases.csv")
    # Hyperparameters SageMaker passes as --key value pairs; unused here since
    # build_pipeline() hardcodes them, but wired through to show the pattern.
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=6)
    args = parser.parse_args()

    data_path = Path(args.train_channel) / args.train_file
    model_dir = Path(args.model_dir)

    metadata = train(data_path, model_dir)
    print(f"SageMaker training job complete. model_version={metadata['model_version']}")


if __name__ == "__main__":
    main()

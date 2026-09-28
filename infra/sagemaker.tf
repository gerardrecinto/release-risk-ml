# Reference IaC only. Nothing in this file has been applied to a real AWS
# account for this portfolio project — no SageMaker resources are running.
# It documents the production topology the local pipeline (release_risk_ml/)
# is designed to map onto, including the canary rollout and rollback path
# described in docs/ROLLBACK.md.

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "model_artifact_s3_uri" {
  description = "S3 URI to the model.tar.gz produced by a SageMaker training job."
  type        = string
}

variable "sagemaker_execution_role_arn" {
  type = string
}

variable "current_variant_name" {
  type    = string
  default = "current"
}

variable "canary_variant_name" {
  type    = string
  default = "canary"
}

variable "canary_weight_percent" {
  description = "Percent of traffic routed to the canary variant during rollout."
  type        = number
  default     = 10
}

resource "aws_sagemaker_model" "release_risk_current" {
  name               = "release-risk-current"
  execution_role_arn = var.sagemaker_execution_role_arn

  primary_container {
    image          = "246618743249.dkr.ecr.${var.aws_region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"
    model_data_url = var.model_artifact_s3_uri
  }
}

resource "aws_sagemaker_endpoint_configuration" "release_risk" {
  name = "release-risk-config"

  # Canary/blue-green: both variants live behind one endpoint, weighted so a
  # bad canary only affects canary_weight_percent of traffic. Promote by
  # flipping weights to 100/0; roll back by flipping them back — no endpoint
  # recreation needed. See docs/ROLLBACK.md.
  production_variants {
    variant_name           = var.current_variant_name
    model_name             = aws_sagemaker_model.release_risk_current.name
    initial_instance_count = 2
    instance_type          = "ml.m5.large"
    initial_variant_weight = 100 - var.canary_weight_percent
  }

  production_variants {
    variant_name           = var.canary_variant_name
    model_name             = aws_sagemaker_model.release_risk_current.name
    initial_instance_count = 1
    instance_type          = "ml.m5.large"
    initial_variant_weight = var.canary_weight_percent
  }
}

resource "aws_sagemaker_endpoint" "release_risk" {
  name                 = "release-risk-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.release_risk.name
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "release-risk-endpoint-p99-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "p99"
  threshold           = 500000 # microseconds; 500ms
  dimensions = {
    EndpointName = aws_sagemaker_endpoint.release_risk.name
    VariantName  = var.current_variant_name
  }
  alarm_description = "p99 model latency exceeded 500ms for 3 consecutive minutes"
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "release-risk-endpoint-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Invocation5XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  dimensions = {
    EndpointName = aws_sagemaker_endpoint.release_risk.name
    VariantName  = var.current_variant_name
  }
  alarm_description = "More than 5 5xx errors in a 1-minute window for 3 consecutive minutes"
}

# SageMaker Model Monitor schedule for data quality drift. References a
# baseline statistics/constraints pair generated from the training set (see
# release_risk_ml/monitoring/drift.py for the equivalent local PSI check).
resource "aws_sagemaker_monitoring_schedule" "data_quality" {
  name = "release-risk-data-quality-schedule"

  monitoring_schedule_config {
    schedule_config {
      schedule_expression = "cron(0 * ? * * *)" # hourly
    }
    monitoring_job_definition_name = "release-risk-data-quality-job"
  }
}

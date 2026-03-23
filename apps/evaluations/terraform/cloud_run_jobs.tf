# Single Cloud Run Job for all evaluations
#
# This job supports two modes:
# 1. Tier mode: Pass EVAL_TIER env var, task count matches tier config
# 2. Ad-hoc mode: Pass EVAL_MODE=ad-hoc with AD_HOC_* env vars
#
# Task count and env vars are overridden at execution time via:
#   gcloud run jobs execute eval --tasks N --update-env-vars "KEY=VALUE"

resource "google_cloud_run_v2_job" "eval" {
  name     = "eval"
  location = var.region

  labels = {
    managed-by = "terraform"
  }

  template {
    # Parallelism set to max - actual task count is overridden at execution time
    # Note: parallelism cannot be overridden at execution, only taskCount can
    parallelism = var.max_parallel_task_count
    task_count  = 1

    template {
      # Use max timeout from all tiers (can't be overridden at execution)
      timeout = "${var.max_task_timeout_minutes * 60}s"

      # Retry failed tasks up to 3 times (Cloud Run default, made explicit)
      max_retries = 3

      # Direct VPC Egress for private network access
      vpc_access {
        network_interfaces {
          network    = "projects/${var.project_id}/global/networks/default"
          subnetwork = "projects/${var.project_id}/regions/${var.region}/subnetworks/default"
        }
        egress = "ALL_TRAFFIC"
      }

      containers {
        image = "us-west1-docker.pkg.dev/${var.project_id}/model-evals/evaluations:${var.image_tag}"

        resources {
          limits = {
            cpu    = "4"
            memory = "8Gi"
          }
        }

        # No EVAL_TIER set here - passed at execution time
        env {
          name  = "LOCAL"
          value = "false" # set to false to persist to db and true to skip db persistance (for testing)
        }

        env {
          name = "LITELLM_PROXY_API_KEY"
          value_source {
            secret_key_ref {
              secret  = "litellm-proxy-api-key"
              version = "latest"
            }
          }
        }

        env {
          name = "PGHOST"
          value_source {
            secret_key_ref {
              secret  = "pghost"
              version = "latest"
            }
          }
        }

        # Database password fetched at runtime from AWS Secrets Manager
        # using DB_SECRET_ARN (supports automatic credential rotation)
        env {
          name = "DB_SECRET_ARN"
          value_source {
            secret_key_ref {
              secret  = "db-secret-arn"
              version = "latest"
            }
          }
        }

        # AWS credentials for accessing Secrets Manager and S3
        env {
          name = "AWS_ACCESS_KEY_ID"
          value_source {
            secret_key_ref {
              secret  = "aws-access-key-id"
              version = "latest"
            }
          }
        }

        env {
          name = "AWS_SECRET_ACCESS_KEY"
          value_source {
            secret_key_ref {
              secret  = "aws-secret-access-key"
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    prevent_destroy = false
  }
}

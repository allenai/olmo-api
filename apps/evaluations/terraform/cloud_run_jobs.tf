# Cloud Run Jobs for each evaluation tier
#
# Each tier runs as a Cloud Run Job with parallel tasks.
# The number of tasks equals the number of models in the tier config.
# Each task uses CLOUD_RUN_TASK_INDEX to select which model to evaluate.

resource "google_cloud_run_v2_job" "eval" {
  for_each = var.tiers

  name     = "eval-${each.key}"
  location = var.region

  labels = {
    tier       = each.key
    managed-by = "terraform"
  }

  template {
    parallelism = each.value.task_count
    task_count  = each.value.task_count

    template {
      timeout = "${each.value.timeout_minutes * 60}s"

      containers {
        image = "us-west1-docker.pkg.dev/${var.project_id}/model-evals/evaluations:${var.image_tag}"

        resources {
          limits = {
            cpu    = "4"
            memory = "8Gi"
          }
        }

        env {
          name  = "EVAL_TIER"
          value = each.key
        }

        env {
          name  = "LOCAL"
          value = "false"
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

        env {
          name = "PGPASSWORD"
          value_source {
            secret_key_ref {
              secret  = "pgpassword"
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    # Prevent destruction without explicit approval
    prevent_destroy = false
  }
}

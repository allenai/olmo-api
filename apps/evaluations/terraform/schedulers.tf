# Cloud Scheduler jobs for tiers that have a schedule defined
#
# Each scheduler triggers the single eval job with tier-specific overrides:
# - taskCount: Number of parallel tasks (models) in the tier
# - env: EVAL_TIER set to the tier name
#
# Uses Cloud Run Jobs API v1 with JSON body for overrides.

resource "google_cloud_scheduler_job" "eval" {
  for_each = { for k, v in var.tiers : k => v if v.schedule != null }

  name      = "eval-${each.key}-schedule"
  schedule  = each.value.schedule
  time_zone = "UTC"
  region    = var.region

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.eval.name}:run"
    http_method = "POST"

    # Override task count and env vars for this tier
    body = base64encode(jsonencode({
      overrides = {
        taskCount = each.value.task_count
        containerOverrides = [{
          env = [
            { name = "EVAL_TIER", value = each.key }
          ]
        }]
      }
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = data.google_compute_default_service_account.default.email
    }
  }

  retry_config {
    retry_count          = 1
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
  }
}

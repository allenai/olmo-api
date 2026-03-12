# Cloud Scheduler jobs for tiers that have a schedule defined
#
# Only creates schedulers for tiers where schedule != null.
# Uses OAuth to authenticate requests to Cloud Run.

resource "google_cloud_scheduler_job" "eval" {
  for_each = { for k, v in var.tiers : k => v if v.schedule != null }

  name      = "eval-${each.key}-schedule"
  schedule  = each.value.schedule
  time_zone = "UTC"
  region    = var.region

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.eval[each.key].name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = data.google_compute_default_service_account.default.email
    }
  }

  # Retry configuration
  retry_config {
    retry_count          = 1
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
  }
}

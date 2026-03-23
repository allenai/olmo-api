output "cloud_run_job_name" {
  description = "Name of the deployed Cloud Run Job"
  value       = google_cloud_run_v2_job.eval.name
}

output "cloud_run_job_uri" {
  description = "URI to execute the Cloud Run Job"
  value       = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.eval.name}:run"
}

output "scheduler_names" {
  description = "Names of the Cloud Scheduler jobs"
  value       = { for k, v in google_cloud_scheduler_job.eval : k => v.name }
}

output "tier_execution_commands" {
  description = "Commands to manually execute each tier"
  value = { for k, v in var.tiers : k => "gcloud run jobs execute ${google_cloud_run_v2_job.eval.name} --region ${var.region} --project ${var.project_id} --tasks ${v.task_count} --update-env-vars EVAL_TIER=${k}" }
}

output "adhoc_execution_example" {
  description = "Example command for ad-hoc evaluation"
  value       = "gcloud run jobs execute ${google_cloud_run_v2_job.eval.name} --region ${var.region} --project ${var.project_id} --tasks 1 --update-env-vars \"EVAL_MODE=ad-hoc,AD_HOC_MODEL=litellm_proxy/openai/Olmo-7B,AD_HOC_TASKS=humaneval:bpb\""
}

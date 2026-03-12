output "cloud_run_job_names" {
  description = "Names of the deployed Cloud Run Jobs"
  value       = { for k, v in google_cloud_run_v2_job.eval : k => v.name }
}

output "cloud_run_job_uris" {
  description = "URIs to execute the Cloud Run Jobs"
  value = { for k, v in google_cloud_run_v2_job.eval : k => "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${v.name}:run" }
}

output "scheduler_names" {
  description = "Names of the Cloud Scheduler jobs"
  value       = { for k, v in google_cloud_scheduler_job.eval : k => v.name }
}

output "manual_execution_commands" {
  description = "Commands to manually execute each job"
  value = { for k, v in google_cloud_run_v2_job.eval : k => "gcloud run jobs execute ${v.name} --region ${var.region} --project ${var.project_id}" }
}

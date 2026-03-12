variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Scheduler"
  type        = string
  default     = "us-west1"
}

variable "image_tag" {
  description = "Container image tag (commit SHA or 'latest')"
  type        = string
  default     = "latest"
}

variable "tiers" {
  description = "Evaluation tier configurations (generated from Python configs)"
  type = map(object({
    task_count      = number
    timeout_minutes = number
    schedule        = optional(string) # null = no scheduler (manual only)
  }))
}

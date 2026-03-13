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

variable "max_task_timeout_minutes" {
  description = "Maximum timeout per Cloud Run task (from longest tier)"
  type        = number
  default     = 360 # 6 hours (full tier default)
}

variable "max_parallel_task_count" {
  description = "Maximum parallel Cloud Run tasks (from largest tier)"
  type        = number
  default     = 10
}

variable "tiers" {
  description = "Evaluation tier configurations (generated from Python configs)"
  type = map(object({
    task_count      = number
    timeout_minutes = number
    schedule        = optional(string) # null = no scheduler (manual only)
  }))
}

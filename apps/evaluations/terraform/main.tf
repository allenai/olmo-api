terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "ai2-skiff2-playground-tf-state"
    prefix = "evaluations"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Default compute service account for Cloud Scheduler
data "google_compute_default_service_account" "default" {}

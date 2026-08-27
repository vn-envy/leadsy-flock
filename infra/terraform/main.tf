# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0 (the "License");

variable "project_id" {
  type    = string
  default = "leadsy-flock"
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "runtime_region" {
  type        = string
  default     = "us-central1"
  description = "Vertex Agent Engine / Veo / Lyria region"
}

variable "service_account" {
  type    = string
  default = "leadsy-agent@leadsy-flock.iam.gserviceaccount.com"
}

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "cloudtrace.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "modelarmor.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_pubsub_topic" "campaign_steps" {
  name       = "campaign-steps"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "campaign_steps_dlq" {
  name       = "campaign-steps-dlq"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "founder_alerts" {
  name       = "founder-alerts"
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "media" {
  name                        = "${var.project_id}-media-${var.region}"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.apis]
}

resource "google_storage_bucket" "logs" {
  name                        = "${var.project_id}-logs-${var.region}"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.apis]
}

resource "google_service_account" "pubsub_push" {
  account_id   = "leadsy-pubsub-push"
  display_name = "Leadsy Pub/Sub push to Cloud Run"
}

# The push subscription itself is created after flock-worker exists
# (scripts/provision_infra.sh with FLOCK_WORKER_URL). Terraform stops
# at topics + IAM so apply stays idempotent before the first deploy.

data "google_project" "this" {
  project_id = var.project_id
}

resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_push.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "agent_datastore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.service_account}"
}

resource "google_project_iam_member" "agent_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.service_account}"
}

resource "google_project_iam_member" "agent_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.service_account}"
}

resource "google_project_iam_member" "agent_armor" {
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = "serviceAccount:${var.service_account}"
}

output "media_bucket" { value = google_storage_bucket.media.name }
output "logs_bucket" { value = google_storage_bucket.logs.name }
output "campaign_steps_topic" { value = google_pubsub_topic.campaign_steps.id }
output "runtime_region" { value = var.runtime_region }

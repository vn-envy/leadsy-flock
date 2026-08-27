# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Runtime configuration. All values come from the environment — never secrets in code."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _req(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    project_id: str
    region: str
    location_global: str
    firestore_database: str
    campaign_topic: str
    dlq_topic: str
    alerts_topic: str
    media_bucket: str
    logs_bucket: str
    armor_location: str
    armor_template: str
    memory_bank_id: str
    memory_bank_location: str
    service_name: str

    @property
    def campaign_topic_path(self) -> str:
        return f"projects/{self.project_id}/topics/{self.campaign_topic}"


def load_settings() -> Settings:
    project = _req("GOOGLE_CLOUD_PROJECT") or _req("GCP_PROJECT_ID")
    return Settings(
        project_id=project,
        region=_req("GCP_REGION", "asia-south1"),
        location_global=_req("GOOGLE_CLOUD_LOCATION", "global"),
        firestore_database=_req("FIRESTORE_DATABASE", "(default)"),
        campaign_topic=_req("CAMPAIGN_STEPS_TOPIC", "campaign-steps"),
        dlq_topic=_req("CAMPAIGN_STEPS_DLQ_TOPIC")
        or _req("CAMPAIGN_DLQ_TOPIC", "campaign-steps-dlq"),
        alerts_topic=_req("FOUNDER_ALERTS_TOPIC", "founder-alerts"),
        media_bucket=_req("MEDIA_BUCKET_NAME", ""),
        logs_bucket=_req("LOGS_BUCKET_NAME", ""),
        armor_location=_req("MODEL_ARMOR_LOCATION", "asia-south1"),
        armor_template=_req("MODEL_ARMOR_TEMPLATE", "leadsy-inbound"),
        memory_bank_id=_req("MEMORY_BANK_ID", ""),
        memory_bank_location=_req("MEMORY_BANK_LOCATION", "us-central1"),
        service_name=_req("K_SERVICE", "flock-api"),
    )

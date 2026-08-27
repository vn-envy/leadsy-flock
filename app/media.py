# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""GCS media writes. One owner: Inka (and Stella's HTML copy)."""

from __future__ import annotations

from google.cloud import storage

from app.settings import load_settings


def put_bytes(path: str, data: bytes, content_type: str) -> str:
    settings = load_settings()
    bucket = settings.media_bucket
    if not bucket:
        return ""
    client = storage.Client(project=settings.project_id or None)
    blob = client.bucket(bucket).blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket}/{path}"


def campaign_path(campaign_id: str, name: str) -> str:
    return f"campaigns/{campaign_id}/{name}"

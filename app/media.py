# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""GCS media writes. Inka stills; harvest sidecar clips/jingles; Stella HTML."""

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


def get_bytes(path: str) -> tuple[bytes, str] | None:
    settings = load_settings()
    bucket = settings.media_bucket
    if not bucket:
        return None
    client = storage.Client(project=settings.project_id or None)
    blob = client.bucket(bucket).blob(path)
    if not blob.exists():
        return None
    return blob.download_as_bytes(), blob.content_type or "application/octet-stream"


def get_campaign_still(campaign_id: str) -> tuple[bytes, str] | None:
    for name in ("still.png", "still.jpg", "still.jpeg", "still.webp"):
        found = get_bytes(campaign_path(campaign_id, name))
        if found:
            return found
    return None


CLIP_NAMES = ("clip.mp4", "clip.bin", "clip.webm")
JINGLE_NAMES = ("jingle.wav", "jingle.mp3", "jingle.bin")


def get_campaign_clip(campaign_id: str) -> tuple[bytes, str] | None:
    for name in CLIP_NAMES:
        found = get_bytes(campaign_path(campaign_id, name))
        if found:
            return found
    return None


def get_campaign_jingle(campaign_id: str) -> tuple[bytes, str] | None:
    for name in JINGLE_NAMES:
        found = get_bytes(campaign_path(campaign_id, name))
        if found:
            return found
    return None


def campaign_asset_exists(campaign_id: str, names: tuple[str, ...]) -> bool:
    settings = load_settings()
    bucket = settings.media_bucket
    if not bucket:
        return False
    client = storage.Client(project=settings.project_id or None)
    bkt = client.bucket(bucket)
    for name in names:
        if bkt.blob(campaign_path(campaign_id, name)).exists():
            return True
    return False


def campaign_path(campaign_id: str, name: str) -> str:
    return f"campaigns/{campaign_id}/{name}"

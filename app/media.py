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


STILL_NAMES = ("still.png", "still.jpg", "still.jpeg", "still.webp")
CLIP_NAMES = ("clip.mp4", "clip.bin", "clip.webm")
JINGLE_NAMES = ("jingle.wav", "jingle.mp3", "jingle.bin")

MEDIA_SLOTS: dict[str, tuple[str, ...]] = {
    "still": STILL_NAMES,
    "still-square": ("still-square.png", "still-square.jpg"),
    "still-feed": ("still-feed.png", "still-feed.jpg"),
    "still-story": ("still-story.png", "still-story.jpg"),
    "still-landscape": ("still-landscape.png", "still-landscape.jpg"),
    "still-detail": ("still-detail.png", "still-detail.jpg"),
    "own-0": ("own-0.jpg", "own-0.png"),
    "own-1": ("own-1.jpg", "own-1.png"),
    "own-2": ("own-2.jpg", "own-2.png"),
    "clip": CLIP_NAMES,
    "clip-square": ("clip-square.mp4",),
    "clip-feed": ("clip-feed.mp4",),
    "clip-story": ("clip-story.mp4",),
    "clip-landscape": ("clip-landscape.mp4",),
    "clip-captioned": ("clip-captioned.mp4",),
    "clip-captioned-en": ("clip-captioned-en.mp4",),
    "clip-en": ("clip-en.mp4",),
    "clip-indic": ("clip-indic.mp4",),
    "clip-proof": ("clip-proof.mp4",),
    "clip-proof-square": ("clip-proof-square.mp4",),
    "clip-proof-feed": ("clip-proof-feed.mp4",),
    "clip-proof-story": ("clip-proof-story.mp4",),
    "clip-proof-landscape": ("clip-proof-landscape.mp4",),
    "clip-proof-en": ("clip-proof-en.mp4",),
    "clip-proof-indic": ("clip-proof-indic.mp4",),
    "jingle": JINGLE_NAMES,
}


def get_campaign_slot(campaign_id: str, slot: str) -> tuple[bytes, str] | None:
    names = MEDIA_SLOTS.get(slot)
    if not names:
        return None
    for name in names:
        found = get_bytes(campaign_path(campaign_id, name))
        if found:
            return found
    return None


def get_campaign_still(campaign_id: str) -> tuple[bytes, str] | None:
    for name in STILL_NAMES:
        found = get_bytes(campaign_path(campaign_id, name))
        if found:
            return found
    return None


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

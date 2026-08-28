# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Sidecar harvest — poll Veo LRO and retry Lyria without blocking Inka."""

from __future__ import annotations

import os
from typing import Any

from google.genai import types

from app import ledger, media
from app.engines import gemini_util as g
from app.engines.inka import _lyria

MAX_ATTEMPTS = int(os.environ.get("HARVEST_MAX_ATTEMPTS", "16"))


_KEEP = {"harvested", "failed", "timed_out", "done_no_bytes"}


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    attempt = int(campaign.get("_harvestAttempt") or 1)
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    assets = dict(inka.get("assets") or {})
    saved = dict(campaign.get("harvestAssets") or {})
    prompts = inka.get("prompts") or {}
    clip = _merge_asset(assets.get("clip"), saved.get("clip"))
    jingle = _merge_asset(assets.get("jingle"), saved.get("jingle"))
    assets["clip"] = clip
    assets["jingle"] = jingle
    errors: list[str] = []

    if clip.get("operation") and not clip.get("gcs") and clip.get("status") not in _KEEP:
        already = False
        try:
            already = bool(campaign_id) and media.campaign_asset_exists(campaign_id, media.CLIP_NAMES)
        except Exception:  # noqa: BLE001
            already = False
        if already:
            clip = dict(clip)
            clip.update(
                {
                    "ok": True,
                    "status": "harvested",
                    "publicPath": f"/media/{campaign_id}/clip",
                    "note": "already in GCS",
                }
            )
        else:
            clip = _poll_veo(clip, campaign_id, errors)
        assets["clip"] = clip

    skip_lyria = os.environ.get("INKA_SKIP_LYRIA", "0") == "1"
    if not skip_lyria and not jingle.get("gcs") and not jingle.get("skipped"):
        if attempt >= 3:
            jingle = dict(jingle)
            jingle["skipped"] = True
            jingle["ok"] = False
            jingle["note"] = jingle.get("note") or "Lyria gave up after retries (often 429 quota)"
            assets["jingle"] = jingle
        else:
            jingle = _lyria(campaign_id, prompts.get("lyria") or "", errors)
            assets["jingle"] = jingle

    clip_pending = bool(
        clip.get("operation") and not clip.get("gcs") and clip.get("status") not in _KEEP
    )
    jingle_pending = (
        not skip_lyria
        and not jingle.get("gcs")
        and not jingle.get("skipped")
        and attempt < MAX_ATTEMPTS
    )
    retry = (clip_pending or jingle_pending) and attempt < MAX_ATTEMPTS
    if attempt >= MAX_ATTEMPTS and clip_pending:
        clip["status"] = "timed_out"
        clip["ok"] = False
        assets["clip"] = clip
        errors.append("veo:harvest_timed_out")

    if campaign_id:
        ledger.upsert_campaign(
            campaign_id,
            {
                "harvestAssets": assets,
                "clipPath": clip.get("publicPath") if clip.get("gcs") or clip.get("status") == "harvested" else None,
                "jinglePath": jingle.get("publicPath") if jingle.get("gcs") else None,
            },
        )

    return {
        "retry": retry,
        "attempt": attempt,
        "maxAttempts": MAX_ATTEMPTS,
        "assets": assets,
        "errors": errors,
        "clip": clip,
        "jingle": jingle,
    }


def _merge_asset(base: Any, saved: Any) -> dict[str, Any]:
    out = dict(base or {})
    extra = dict(saved or {})
    if extra.get("gcs") or extra.get("skipped") or extra.get("status") in _KEEP:
        out.update(extra)
    return out


def _poll_veo(clip: dict[str, Any], campaign_id: str, errors: list[str]) -> dict[str, Any]:
    name = clip.get("operation")
    if not name:
        return clip
    try:
        client = g.media_client()
        operation = client.operations.get(types.GenerateVideosOperation(name=name))
        out = dict(clip)
        out["done"] = bool(getattr(operation, "done", False))
        if getattr(operation, "error", None):
            out["ok"] = False
            out["status"] = "failed"
            out["error"] = str(operation.error)[:300]
            return out
        if not getattr(operation, "done", False):
            out["status"] = "started"
            out["ok"] = True
            return out
        data, mime = _video_bytes(operation)
        if not data:
            out["ok"] = False
            out["status"] = "done_no_bytes"
            errors.append("veo:done_no_bytes")
            return out
        uri = media.put_bytes(media.campaign_path(campaign_id, "clip.mp4"), data, mime or "video/mp4")
        out.update(
            {
                "ok": True,
                "status": "harvested",
                "gcs": uri,
                "bytes": len(data),
                "mime": mime or "video/mp4",
                "publicPath": f"/media/{campaign_id}/clip",
                "model": g.VEO_MODEL,
            }
        )
        return out
    except Exception as exc:  # noqa: BLE001
        errors.append(f"veo:{type(exc).__name__}:{exc}")
        out = dict(clip)
        out["error"] = str(exc)[:300]
        out["status"] = "poll_error"
        return out


def _video_bytes(operation: Any) -> tuple[bytes | None, str | None]:
    response = getattr(operation, "response", None) or getattr(operation, "result", None)
    generated = getattr(response, "generated_videos", None) if response else None
    if not generated:
        return None, None
    video = generated[0].video
    data = getattr(video, "video_bytes", None)
    mime = getattr(video, "mime_type", None) or "video/mp4"
    if data:
        return data, mime
    uri = getattr(video, "uri", None) or ""
    if uri.startswith("gs://"):
        return _download_gs(uri)
    return None, None


def _download_gs(uri: str) -> tuple[bytes | None, str | None]:
    from google.cloud import storage

    without = uri[5:]
    bucket, _, path = without.partition("/")
    if not bucket or not path:
        return None, None
    blob = storage.Client().bucket(bucket).blob(path)
    if not blob.exists():
        return None, None
    return blob.download_as_bytes(), blob.content_type or "video/mp4"

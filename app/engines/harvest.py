# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Sidecar harvest — poll Veo LRO and retry Lyria without blocking Inka."""

from __future__ import annotations

import os
from typing import Any

from google.genai import types

from app import ledger, media
from app.captions import burn_story_captions
from app.derive import derive_videos
from app.engines import gemini_util as g
from app.engines.inka import _lyria, _veo_start

MAX_ATTEMPTS = int(os.environ.get("HARVEST_MAX_ATTEMPTS", "24"))


_KEEP = {"harvested", "failed", "timed_out"}


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
            try:
                clip["derivatives"] = derive_videos(campaign_id, "clip.mp4")
            except Exception as extra:  # noqa: BLE001
                errors.append(f"derive:{type(extra).__name__}:{extra}")
            assets["clip"] = clip
            # fall through to lyria / persist
        else:
            clip = _poll_veo(clip, campaign_id, errors)
            if clip.get("status") == "done_no_bytes":
                restarted = _restart_veo(clip, campaign_id, inka, errors)
                clip = restarted or {**clip, "status": "failed", "ok": False}
            assets["clip"] = clip

    if (
        campaign_id
        and (clip.get("gcs") or clip.get("status") == "harvested")
        and not (clip.get("derivatives") or {}).get("ok")
    ):
        try:
            clip = dict(clip)
            clip["derivatives"] = derive_videos(campaign_id, "clip.mp4")
            assets["clip"] = clip
        except Exception as extra:  # noqa: BLE001
            errors.append(f"derive:{type(extra).__name__}:{extra}")

    if campaign_id and (clip.get("gcs") or clip.get("status") == "harvested"):
        if not (clip.get("captions") or {}).get("ok"):
            copy = inka.get("copy") or {}
            vo = str(copy.get("voIndic") or copy.get("voEn") or "")
            try:
                cap = burn_story_captions(campaign_id, vo, inka.get("locale") or {})
                if not cap.get("ok"):
                    story = media.get_bytes(media.campaign_path(campaign_id, "clip-story.mp4"))
                    if story:
                        uri = media.put_bytes(
                            media.campaign_path(campaign_id, "clip-captioned.mp4"),
                            story[0],
                            "video/mp4",
                        )
                        cap = {
                            "ok": True,
                            "gcs": uri,
                            "publicPath": f"/media/{campaign_id}/clip-captioned",
                            "note": "uncaptioned fallback",
                        }
                clip = dict(clip)
                clip["captions"] = cap
                assets["clip"] = clip
            except Exception as extra:  # noqa: BLE001
                errors.append(f"captions:{type(extra).__name__}:{extra}")

    skip_lyria = os.environ.get("INKA_SKIP_LYRIA", "0") == "1"
    if not skip_lyria and not jingle.get("gcs") and not jingle.get("skipped"):
        if attempt >= 3:
            jingle = dict(jingle)
            jingle["skipped"] = True
            jingle["pending"] = False
            jingle["ok"] = False
            jingle["note"] = "Lyria gave up after retries (often 429 quota)"
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
    """Harvest state wins — including a fallback LRO that replaced Inka's original."""
    out = dict(base or {})
    extra = dict(saved or {})
    if extra:
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
        data, mime = _video_bytes(operation, client)
        if not data:
            reasons = _rai_reasons(operation)
            out["ok"] = False
            out["status"] = "done_no_bytes"
            out["raiReasons"] = reasons
            errors.append("veo:done_no_bytes" + (f":{reasons[0][:180]}" if reasons else ""))
            return out
        uri = media.put_bytes(media.campaign_path(campaign_id, "clip.mp4"), data, mime or "video/mp4")
        derived = {}
        try:
            derived = derive_videos(campaign_id, "clip.mp4")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"derive:{type(exc).__name__}:{exc}")
        out.update(
            {
                "ok": True,
                "status": "harvested",
                "gcs": uri,
                "bytes": len(data),
                "mime": mime or "video/mp4",
                "publicPath": f"/media/{campaign_id}/clip",
                "model": g.VEO_MODEL,
                "derivatives": derived,
            }
        )
        return out
    except Exception as exc:  # noqa: BLE001
        errors.append(f"veo:{type(exc).__name__}:{exc}")
        out = dict(clip)
        out["error"] = str(exc)[:300]
        out["status"] = "poll_error"
        return out


def _rai_reasons(operation: Any) -> list[str]:
    response = getattr(operation, "response", None) or getattr(operation, "result", None)
    raw = getattr(response, "rai_media_filtered_reasons", None) if response else None
    return [str(x) for x in (raw or []) if x]


def _restart_veo(
    clip: dict[str, Any],
    campaign_id: str,
    inka: dict[str, Any],
    errors: list[str],
) -> dict[str, Any] | None:
    """RAI often blocks ASSET refs that imply people. Start the next fallback LRO."""
    copy = inka.get("copy") or {}
    prompts = inka.get("prompts") or {}
    if clip.get("usedRefs"):
        sequence: tuple[tuple[bool, str], ...] = ((False, "9:16"), (False, "16:9"))
    elif str(clip.get("aspectRatio") or "") == "9:16":
        sequence = ((False, "16:9"),)
    else:
        return None
    started = _veo_start(
        campaign_id,
        str(prompts.get("veo") or ""),
        errors,
        refs=[],
        vo_line=str(copy.get("voIndic") or copy.get("voEn") or ""),
        sequence=sequence,
    )
    if not started.get("operation"):
        return None
    started["fallbackFrom"] = clip.get("status")
    started["priorRai"] = clip.get("raiReasons") or []
    started["fallbackStage"] = int(clip.get("fallbackStage") or 0) + 1
    started["priorOperation"] = clip.get("operation")
    return started


def _video_bytes(operation: Any, client: Any | None = None) -> tuple[bytes | None, str | None]:
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
    if client and uri:
        try:
            client.files.download(file=video)
            data = getattr(video, "video_bytes", None)
            if data:
                return data, mime
        except Exception:  # noqa: BLE001
            pass
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

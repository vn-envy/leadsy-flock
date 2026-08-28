# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka — copy + still + Veo clip + Lyria sting, BrandSpec-conditioned."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from google.genai import types

from app import ledger, media
from app.engines import gemini_util as g


COPY_PROMPT = """You are Inka, the artist of a local-SMB agency in India.
Write campaign creative. Return ONLY JSON:
{{
  "draftHeadline": "a punchy first-pass line that a junior copywriter might overclaim (include one banned-pattern word like guaranteed/miracle if you would have been tempted)",
  "headline": "compliant headline, no guaranteed outcomes, no medical claims, specific to this business",
  "subhead": "one supporting sentence",
  "primaryText": "2-3 sentences for a Meta primary text, under 125 words",
  "cta": "short CTA",
  "veoPrompt": "a 4-second locked-off cinematic prompt, no people faces, no on-screen text",
  "imagePrompt": "still photograph prompt, BrandSpec palette, no text in the image",
  "lyriaPrompt": "2-second instrumental sting, no vocals"
}}

Never put a real person's name, email, or phone in the copy.
BrandSpec: {brand}
Evidence (summaries only): {evidence}
Policy memory from the gate (honor these): {policy}
Business: {business} in {geo}. Goal: {goal}. Audience: {audience}.
Attempt: {attempt}
"""


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    try:
        return _run_inner(campaign)
    except Exception as exc:  # noqa: BLE001 — never fail the flock on a media glitch
        brief = campaign.get("brief") or {}
        name = brief.get("businessName") or "the business"
        return {
            "model": g.TEXT_MODEL,
            "copy": {
                "draftHeadline": "Guaranteed transformation this month",
                "headline": f"{name} — evenings that fit your commute",
                "subhead": "Local, honest, no miracle claims.",
                "primaryText": str(brief.get("goal") or "")[:240],
                "cta": "See evening slots",
            },
            "assets": {},
            "errors": [f"{type(exc).__name__}:{exc}"],
        }


def _run_inner(campaign: dict[str, Any]) -> dict[str, Any]:
    brief = campaign.get("brief") or {}
    scout = _scout_payload(campaign["id"]) if campaign.get("id") else {}
    brand = scout.get("brandSpec") or {}
    evidence = scout.get("evidence") or []
    policy = _policy_lines(campaign.get("id") or "")
    snippets = "; ".join(
        f"{e.get('title')}: {str(e.get('snippet') or '')[:180]}" for e in evidence[:6]
    )
    prompt = COPY_PROMPT.format(
        brand=str(brand),
        evidence=snippets.replace("{", "(").replace("}", ")") or "none yet",
        policy=(policy or "none").replace("{", "(").replace("}", ")"),
        business=brief.get("businessName") or "the business",
        geo=brief.get("geo") or "",
        goal=brief.get("goal") or "",
        audience=brief.get("audience") or "",
        attempt=campaign.get("inkaRevisions") or 1,
    )
    errors: list[str] = []
    client = g.text_client()
    try:
        text_resp = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8),
        )
        copy = g.extract_json(g.response_text(text_resp))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"copy:{type(exc).__name__}:{exc}")
        copy = None
    if not isinstance(copy, dict):
        copy = {
            "draftHeadline": "Guaranteed transformation this month",
            "headline": f"{brief.get('businessName') or 'Us'} — evenings that fit your commute",
            "subhead": "Local, honest, no miracle claims.",
            "primaryText": str(brief.get("goal") or "")[:240],
            "cta": "See evening slots",
            "veoPrompt": "Empty modern gym, morning light, no people, no text.",
            "imagePrompt": "Wide still of a calm gym interior, gold and charcoal palette, no text.",
            "lyriaPrompt": "Short bright ukulele sting, no vocals.",
        }

    campaign_id = campaign.get("id") or "campaign"
    assets: dict[str, Any] = {}
    skip_veo = os.environ.get("INKA_SKIP_VEO", "0") == "1"
    skip_still = os.environ.get("INKA_SKIP_STILL", "0") == "1"
    skip_lyria = os.environ.get("INKA_SKIP_LYRIA", "0") == "1"

    if skip_still:
        assets["still"] = {"ok": False, "skipped": True, "model": g.IMAGE_MODEL}
    else:
        assets["still"] = _still(campaign_id, copy.get("imagePrompt") or "", brand, errors)
    if skip_veo:
        assets["clip"] = {"ok": False, "skipped": True, "model": g.VEO_MODEL, "note": "INKA_SKIP_VEO=1"}
    else:
        assets["clip"] = _veo_start(campaign_id, copy.get("veoPrompt") or "", errors)
    if skip_lyria:
        assets["jingle"] = {
            "ok": False,
            "skipped": True,
            "pending": False,
            "model": g.LYRIA_MODEL,
            "note": "INKA_SKIP_LYRIA=1",
        }
    else:
        assets["jingle"] = {
            "ok": False,
            "pending": True,
            "model": g.LYRIA_MODEL,
            "note": "Lyria runs on inka_harvest so quota 429 cannot timeout Inka",
        }

    return {
        "model": g.TEXT_MODEL,
        "copy": {
            "draftHeadline": copy.get("draftHeadline"),
            "headline": copy.get("headline"),
            "subhead": copy.get("subhead"),
            "primaryText": copy.get("primaryText"),
            "cta": copy.get("cta"),
        },
        "prompts": {
            "veo": copy.get("veoPrompt"),
            "image": copy.get("imagePrompt"),
            "lyria": copy.get("lyriaPrompt"),
        },
        "brandSpec": brand,
        "assets": assets,
        "errors": errors,
    }


def _scout_payload(campaign_id: str) -> dict[str, Any]:
    row = ledger.get_receipt(campaign_id, "scout") or {}
    return row.get("payload") or {}


def _policy_lines(campaign_id: str) -> str:
    if not campaign_id:
        return ""
    try:
        rows = ledger.list_memories(campaign_id, kind="policy")
    except Exception:  # noqa: BLE001
        return ""
    return " | ".join(str(r.get("text") or "") for r in rows[:8])


def _still(campaign_id: str, prompt: str, brand: dict, errors: list[str]) -> dict[str, Any]:
    palette = ", ".join(brand.get("palette") or [])
    full = f"{prompt}\nColor palette: {palette}. No letters, logos, watermarks, or people."
    attempts = (
        (g.image_client, g.IMAGE_MODEL),
        (g.media_client, g.IMAGE_FALLBACK_MODEL),
    )
    last_error = ""
    for client_fn, model in attempts:
        try:
            client = client_fn()
            resp = client.models.generate_content(
                model=model,
                contents=full,
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            blobs = g.inline_bytes(resp)
            if not blobs:
                last_error = f"{model}:no_image_bytes"
                continue
            data, mime = blobs[0]
            ext = "png" if "png" in (mime or "") else "jpg"
            path = media.campaign_path(campaign_id, f"still.{ext}")
            uri = media.put_bytes(path, data, mime)
            return {
                "ok": True,
                "model": model,
                "gcs": uri,
                "bytes": len(data),
                "mime": mime,
                "publicPath": f"/media/{campaign_id}/still",
            }
        except Exception as exc:  # noqa: BLE001
            last_error = f"{model}:{type(exc).__name__}:{exc}"
            continue
    errors.append(f"still:{last_error}")
    return {"ok": False, "model": g.IMAGE_MODEL, "error": last_error[:300]}


def _call_timeout(fn, seconds: int, fallback: Any) -> Any:
    """Time-box a Vertex call without blocking shutdown on the leftover thread."""
    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(fn)
    try:
        return fut.result(timeout=seconds)
    except FuturesTimeout:
        if isinstance(fallback, dict):
            out = dict(fallback)
            out["error"] = f"timeout_{seconds}s"
            return out
        return fallback
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _veo_start(campaign_id: str, prompt: str, errors: list[str]) -> dict[str, Any]:
    """Kick off Veo without blocking the rest of the flock."""
    t0 = time.time()
    try:
        client = g.media_client()
        operation = client.models.generate_videos(
            model=g.VEO_MODEL,
            prompt=prompt or "Empty modern gym, morning light, no people, no text.",
            config=types.GenerateVideosConfig(number_of_videos=1, duration_seconds=4),
        )
        return {
            "ok": True,
            "model": g.VEO_MODEL,
            "status": "started" if not getattr(operation, "done", False) else "done",
            "operation": getattr(operation, "name", None),
            "seconds": round(time.time() - t0, 1),
            "campaignId": campaign_id,
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"veo:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.VEO_MODEL, "error": str(exc)[:300]}


def _lyria(campaign_id: str, prompt: str, errors: list[str]) -> dict[str, Any]:
    try:
        client = g.media_client()
        resp = client.models.generate_content(
            model=g.LYRIA_MODEL,
            contents=prompt or "A 2-second bright instrumental sting, no vocals.",
            config=types.GenerateContentConfig(response_modalities=["AUDIO"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            errors.append("lyria:no_audio")
            return {"ok": False, "model": g.LYRIA_MODEL}
        data, mime = blobs[0]
        ext = "wav" if "wav" in (mime or "") else "bin"
        uri = media.put_bytes(media.campaign_path(campaign_id, f"jingle.{ext}"), data, mime)
        return {
            "ok": True,
            "model": g.LYRIA_MODEL,
            "gcs": uri,
            "bytes": len(data),
            "mime": mime,
            "publicPath": f"/media/{campaign_id}/jingle",
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"lyria:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.LYRIA_MODEL, "error": str(exc)[:300], "quotaLikely": "429" in str(exc)}

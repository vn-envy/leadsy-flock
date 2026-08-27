# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka — copy + still + Veo clip + Lyria sting, BrandSpec-conditioned."""

from __future__ import annotations

import time
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
    brief = campaign.get("brief") or {}
    scout = _scout_payload(campaign["id"]) if campaign.get("id") else {}
    brand = scout.get("brandSpec") or {}
    evidence = scout.get("evidence") or []
    policy = _policy_lines(campaign.get("id") or "")
    snippets = "; ".join(
        f"{e.get('title')}: {e.get('snippet')}" for e in evidence[:6]
    )
    prompt = COPY_PROMPT.format(
        brand=brand,
        evidence=snippets or "none yet",
        policy=policy or "none",
        business=brief.get("businessName") or "the business",
        geo=brief.get("geo") or "",
        goal=brief.get("goal") or "",
        audience=brief.get("audience") or "",
        attempt=campaign.get("inkaRevisions") or 1,
    )
    text_resp = g.text_client().models.generate_content(
        model=g.TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.8),
    )
    try:
        copy = g.extract_json(g.response_text(text_resp))
    except Exception:
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
    errors: list[str] = []

    assets["still"] = _still(campaign_id, copy.get("imagePrompt") or "", brand, errors)
    assets["clip"] = _veo(campaign_id, copy.get("veoPrompt") or "", errors)
    assets["jingle"] = _lyria(campaign_id, copy.get("lyriaPrompt") or "", errors)

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
    rows = ledger.list_memories(campaign_id, kind="policy")
    return " | ".join(str(r.get("text") or "") for r in rows[:8])


def _still(campaign_id: str, prompt: str, brand: dict, errors: list[str]) -> dict[str, Any]:
    palette = ", ".join(brand.get("palette") or [])
    full = f"{prompt}\nColor palette: {palette}. No letters, logos, or watermarks."
    try:
        resp = g.media_client().models.generate_content(
            model=g.IMAGE_MODEL,
            contents=full,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            errors.append("still:no_image_bytes")
            return {"ok": False, "model": g.IMAGE_MODEL}
        data, mime = blobs[0]
        ext = "png" if "png" in mime else "jpg"
        path = media.campaign_path(campaign_id, f"still.{ext}")
        uri = media.put_bytes(path, data, mime)
        return {"ok": True, "model": g.IMAGE_MODEL, "gcs": uri, "bytes": len(data), "mime": mime}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"still:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.IMAGE_MODEL, "error": str(exc)[:300]}


def _veo(campaign_id: str, prompt: str, errors: list[str]) -> dict[str, Any]:
    wait = int(__import__("os").environ.get("VEO_WAIT_SECONDS", "90"))
    t0 = time.time()
    try:
        client = g.media_client()
        operation = client.models.generate_videos(
            model=g.VEO_MODEL,
            prompt=prompt or "Empty modern gym, morning light, no people, no text.",
            config=types.GenerateVideosConfig(number_of_videos=1, duration_seconds=4),
        )
        deadline = time.time() + wait
        while not operation.done and time.time() < deadline:
            time.sleep(6)
            operation = client.operations.get(operation)
        elapsed = round(time.time() - t0, 1)
        if not operation.done:
            return {
                "ok": True,
                "model": g.VEO_MODEL,
                "status": "started_not_finished",
                "operation": getattr(operation, "name", None),
                "seconds": elapsed,
            }
        response = operation.response
        generated = getattr(response, "generated_videos", None) if response else None
        if not generated:
            errors.append("veo:no_video")
            return {"ok": False, "model": g.VEO_MODEL, "seconds": elapsed}
        video = generated[0].video
        data = getattr(video, "video_bytes", None)
        if not data:
            errors.append("veo:empty_bytes")
            return {"ok": False, "model": g.VEO_MODEL, "seconds": elapsed}
        uri = media.put_bytes(media.campaign_path(campaign_id, "clip.mp4"), data, "video/mp4")
        return {
            "ok": True,
            "model": g.VEO_MODEL,
            "gcs": uri,
            "bytes": len(data),
            "seconds": elapsed,
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"veo:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.VEO_MODEL, "error": str(exc)[:300]}


def _lyria(campaign_id: str, prompt: str, errors: list[str]) -> dict[str, Any]:
    try:
        resp = g.media_client().models.generate_content(
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
        return {"ok": True, "model": g.LYRIA_MODEL, "gcs": uri, "bytes": len(data), "mime": mime}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"lyria:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.LYRIA_MODEL, "error": str(exc)[:300], "quotaLikely": "429" in str(exc)}

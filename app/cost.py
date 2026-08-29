# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""List-price cost engine. Not an invoice — Vertex SKUs we actually call."""

from __future__ import annotations

import os
from typing import Any

from app import ledger

# USD per unit. Public Vertex / Gemini list (Aug 2026). Override via env.
USD_INR = float(os.environ.get("USD_INR", "85"))
FLASH_IN_PER_M = float(os.environ.get("COST_FLASH_IN_PER_M", "1.50"))
FLASH_OUT_PER_M = float(os.environ.get("COST_FLASH_OUT_PER_M", "9.00"))
IMAGE_PER_1K = float(os.environ.get("COST_IMAGE_PER_1K", "0.067"))
VEO_PER_SEC = float(os.environ.get("COST_VEO_PER_SEC", "0.40"))
VEO_SECONDS = float(os.environ.get("COST_VEO_SECONDS", "8"))
TTS_PER_M = float(os.environ.get("COST_TTS_PER_M", "15.0"))
LYRIA_PER_CLIP = float(os.environ.get("COST_LYRIA_PER_CLIP", "0.06"))
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-generate-001")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
LYRIA_MODEL = os.environ.get("LYRIA_MODEL", "lyria-002")


def usage_from_response(response: Any, *, model: str, kind: str = "text") -> dict[str, Any]:
    um = getattr(response, "usage_metadata", None)
    if um is None:
        um = getattr(response, "usageMetadata", None)
    prompt = _num(um, "prompt_token_count", "prompt_tokens", "promptTokenCount")
    cand = _num(um, "candidates_token_count", "candidates_tokens", "candidatesTokenCount")
    total = _num(um, "total_token_count", "total_tokens", "totalTokenCount") or (prompt + cand)
    thoughts = _num(um, "thoughts_token_count", "thoughtsTokenCount")
    return {
        "model": model,
        "kind": kind,
        "inputTokens": prompt,
        "outputTokens": cand,
        "totalTokens": total,
        "thoughtsTokens": thoughts,
        "usd": round(_text_usd(model, prompt, cand, kind), 6),
    }


def merge_usage(payload: dict[str, Any], *blobs: dict[str, Any] | None) -> dict[str, Any]:
    rows = list(payload.get("usage") or [])
    for blob in blobs:
        if blob and (blob.get("inputTokens") or blob.get("outputTokens") or blob.get("kind")):
            rows.append(blob)
    if rows:
        payload["usage"] = rows
    return payload


def estimate_campaign(
    campaign_id: str,
    receipts: list[dict[str, Any]] | None = None,
    campaign: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if receipts is None:
        receipts = ledger.list_receipts(campaign_id)
    if not isinstance(receipts, list):
        receipts = []
    lines: list[dict[str, Any]] = []
    for rec in receipts:
        payload = rec.get("payload") if isinstance(rec, dict) else None
        if not isinstance(payload, dict):
            continue
        for row in payload.get("usage") or []:
            if isinstance(row, dict):
                lines.append({**row, "step": rec.get("step")})
        lines.extend(_infer_media(rec.get("step") or "", payload))

    # Dedupe inferred Veo/TTS/Lyria (inka + harvest both carry assets).
    lines = _dedupe_media(lines)
    usd = round(sum(float(x.get("usd") or 0) for x in lines), 4)
    inr = round(usd * USD_INR)
    if campaign is None:
        fetched = ledger.get_campaign(campaign_id) or {}
        campaign = fetched if isinstance(fetched, dict) else {}
    quoted = 0
    if isinstance(campaign, dict):
        quoted = int((campaign.get("engineConfig") or {}).get("price_inr") or campaign.get("quotedInr") or 0)
    return {
        "campaignId": campaign_id,
        "quotedInr": quoted,
        "estimatedUsd": usd,
        "estimatedInr": inr,
        "fx": USD_INR,
        "lines": lines,
        "note": "Vertex list-price reconstruction, not a Google invoice.",
        "marginInr": quoted - inr if quoted else None,
    }


def owner_cost_blurb(est: dict[str, Any]) -> dict[str, Any]:
    """Sanitized for the studio. No SKU dump, no fake invoice."""
    quoted = int(est.get("quotedInr") or 0)
    inr = int(est.get("estimatedInr") or 0)
    if inr <= 0:
        band = "Films still rendering — production cost lands when Veo finishes."
    elif inr < 400:
        band = f"about ₹{max(200, inr - 80)}–₹{inr + 120}"
    else:
        lo = max(200, int(inr * 0.85))
        hi = int(inr * 1.2)
        band = f"about ₹{lo}–₹{hi}"
    return {
        "quotedInr": quoted,
        "productionBand": band,
        "note": (
            "Quoted is what you pay us. Production band is our model cost to run "
            "this kit — not a Vertex invoice passed through to you."
        ),
    }


def rollup_campaign(campaign_id: str) -> dict[str, Any] | None:
    if not campaign_id:
        return None
    est = estimate_campaign(campaign_id)
    ledger.upsert_campaign(
        campaign_id,
        {
            "costUsd": est["estimatedUsd"],
            "costInr": est["estimatedInr"],
            "quotedInr": est["quotedInr"],
        },
    )
    return est


def _text_usd(model: str, inp: int, out: int, kind: str) -> float:
    if kind == "image":
        return IMAGE_PER_1K  # one output image, ~1K tokens
    if kind == "tts":
        return (out / 1_000_000.0) * TTS_PER_M
    if "image" in (model or ""):
        return IMAGE_PER_1K
    return (inp / 1_000_000.0) * FLASH_IN_PER_M + (out / 1_000_000.0) * FLASH_OUT_PER_M


def _infer_media(step: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
    clip = payload.get("clip") if isinstance(payload.get("clip"), dict) else assets.get("clip")
    proof = payload.get("clipProof") if isinstance(payload.get("clipProof"), dict) else assets.get("clipProof")
    jingle = payload.get("jingle") if isinstance(payload.get("jingle"), dict) else assets.get("jingle")
    if _film_done(clip):
        lines.append(_veo_line("place"))
        voices = (clip or {}).get("voices") or {}
        lines.extend(_tts_lines(voices))
    if _film_done(proof):
        lines.append(_veo_line("proof"))
        voices = (proof or {}).get("voices") or {}
        lines.extend(_tts_lines(voices))
    if isinstance(jingle, dict) and (jingle.get("gcs") or jingle.get("ok")) and not jingle.get("skipped"):
        lines.append(
            {
                "model": LYRIA_MODEL,
                "kind": "lyria",
                "usd": LYRIA_PER_CLIP,
                "note": "lyria clip",
            }
        )
    still = assets.get("still") if isinstance(assets.get("still"), dict) else None
    if still and still.get("ok") and still.get("origin") in {"generate", "gemini"}:
        lines.append({"model": IMAGE_MODEL, "kind": "image", "usd": IMAGE_PER_1K, "note": "generated still"})
    return lines


def _film_done(clip: Any) -> bool:
    if not isinstance(clip, dict):
        return False
    return bool(clip.get("gcs") or clip.get("ok") or clip.get("status") in {"harvested"})


def _veo_line(note: str) -> dict[str, Any]:
    usd = round(VEO_PER_SEC * VEO_SECONDS, 4)
    return {
        "model": VEO_MODEL,
        "kind": "veo",
        "seconds": VEO_SECONDS,
        "usd": usd,
        "note": f"{note} 8s + audio",
    }


def _tts_lines(voices: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key in ("en", "indic"):
        rec = voices.get(key) if isinstance(voices, dict) else None
        if isinstance(rec, dict) and rec.get("ok"):
            tokens = int(rec.get("outputTokens") or 400)
            out.append(
                {
                    "model": rec.get("model") or "gemini-2.5-flash-preview-tts",
                    "kind": "tts",
                    "outputTokens": tokens,
                    "usd": round((tokens / 1_000_000.0) * TTS_PER_M, 6),
                    "note": f"tts {key}",
                }
            )
    return out


def _dedupe_media(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for row in lines:
        key = (row.get("kind"), row.get("note"), row.get("model"), row.get("step"))
        if row.get("kind") in {"veo", "tts", "lyria", "image"}:
            key = (row.get("kind"), row.get("note"), row.get("model"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _num(obj: Any, *names: str) -> int:
    if obj is None:
        return 0
    for name in names:
        val = getattr(obj, name, None)
        if val is None and isinstance(obj, dict):
            val = obj.get(name)
        if val is None:
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return 0

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka-Adapt — one gated master → Meta / Google kit. Never auto-posted."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app import ledger
from app.settings import load_settings


CHANNELS = (
    {
        "id": "meta_feed",
        "platform": "meta",
        "placement": "feed",
        "aspect": "1:1",
        "primaryMax": 125,
        "headlineMax": 40,
    },
    {
        "id": "meta_reel",
        "platform": "meta",
        "placement": "reel",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
    },
    {
        "id": "google_rsa",
        "platform": "google",
        "placement": "search",
        "aspect": "text",
        "headlineMax": 30,
        "descriptionMax": 90,
    },
)


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    stella = (ledger.get_receipt(campaign_id, "stella") or {}).get("payload") or {}
    copy = inka.get("copy") or {}
    landing = stella.get("url") or stella.get("landing") or ""
    variants = [variant(ch, copy, landing, campaign_id) for ch in CHANNELS]
    return {
        "autopost": False,
        "note": "Ready to upload. Owner makes the final click on their own channels.",
        "landing": landing,
        "variants": variants,
        "assets": inka.get("assets") or {},
    }


def variant(channel: dict[str, Any], copy: dict[str, Any], landing: str, campaign_id: str) -> dict[str, Any]:
    headline = _clip(str(copy.get("headline") or ""), int(channel.get("headlineMax") or 40))
    primary = _clip(str(copy.get("primaryText") or copy.get("subhead") or ""), int(channel.get("primaryMax") or 125))
    cta = str(copy.get("cta") or "Learn more")
    utm = _utm(landing, campaign_id, channel["id"])
    lint = _lint(channel, headline, primary)
    block: dict[str, Any] = {
        "id": channel["id"],
        "platform": channel["platform"],
        "placement": channel["placement"],
        "aspect": channel["aspect"],
        "headline": headline,
        "primaryText": primary,
        "cta": cta,
        "utmUrl": utm,
        "lint": lint,
        "charCounts": {
            "headline": len(headline),
            "primaryText": len(primary),
        },
    }
    if channel["id"] == "google_rsa":
        desc = _clip(str(copy.get("subhead") or primary), int(channel.get("descriptionMax") or 90))
        block["description"] = desc
        block["charCounts"]["description"] = len(desc)
        block["headlines"] = [headline, _clip(cta, 30), _clip("Evenings near you", 30)]
    return block


def _clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    return text[: max(0, n - 1)].rstrip() + "…"


def _utm(landing: str, campaign_id: str, variant: str) -> str:
    s = load_settings()
    base = landing or __import__("os").environ.get("APP_URL") or ""
    if base and not base.startswith("http"):
        api = __import__("os").environ.get("APP_URL") or ""
        base = f"{api.rstrip('/')}{landing}"
    if not base:
        return ""
    sep = "&" if "?" in base else "?"
    return (
        f"{base}{sep}utm_source={quote(variant.split('_')[0])}"
        f"&utm_medium=paid&utm_campaign={quote(campaign_id)}&utm_content={quote(variant)}"
    )


def _lint(channel: dict[str, Any], headline: str, primary: str) -> dict[str, Any]:
    issues = []
    if any(w in (headline + primary).lower() for w in ("guaranteed", "miracle", "cure")):
        issues.append("claims")
    if channel["platform"] == "meta" and len(primary) > int(channel.get("primaryMax") or 125):
        issues.append("primary_too_long")
    return {"ok": not issues, "issues": issues}

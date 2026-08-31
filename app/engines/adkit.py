# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka-Adapt — one gated master → Meta / Google / WhatsApp kit. Never auto-posted."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app import ledger
from app.design import resolve_theme
from app.derive import PIXEL_BOXES
from app.kit_ui import render_kit


CHANNELS = (
    {
        "id": "meta_feed",
        "platform": "meta",
        "placement": "feed",
        "aspect": "4:5",
        "primaryMax": 125,
        "headlineMax": 40,
        "stillSlot": "still-feed",
        "clipSlot": "clip-feed",
        "proofClipSlot": "clip-proof-feed",
    },
    {
        "id": "meta_square",
        "platform": "meta",
        "placement": "carousel",
        "aspect": "1:1",
        "primaryMax": 125,
        "headlineMax": 40,
        "stillSlot": "still-square",
        "clipSlot": "clip-square",
        "proofClipSlot": "clip-proof-square",
    },
    {
        "id": "meta_reel",
        "platform": "meta",
        "placement": "reel",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-indic",
        "clipSlotEn": "clip-en",
        "proofClipSlot": "clip-proof-indic",
        "proofClipSlotEn": "clip-proof-en",
    },
    {
        "id": "whatsapp_status",
        "platform": "whatsapp",
        "placement": "status",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-indic",
        "clipSlotEn": "clip-en",
        "proofClipSlot": "clip-proof-indic",
        "proofClipSlotEn": "clip-proof-en",
        "organic": True,
    },
    {
        "id": "google_display",
        "platform": "google",
        "placement": "display",
        "aspect": "1.91:1",
        "primaryMax": 90,
        "headlineMax": 30,
        "stillSlot": "still-landscape",
        "clipSlot": "clip-landscape",
        "proofClipSlot": "clip-proof-landscape",
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
    brand = inka.get("brandSpec") or {}
    locale = inka.get("locale") or {}
    shelf = inka.get("shelf") or []
    landing = stella.get("url") or stella.get("landing") or ""
    shown = dict(campaign)
    resolved = str(inka.get("resolvedName") or "").strip()
    if resolved:
        shown["brief"] = {**(campaign.get("brief") or {}), "businessName": resolved}
    variants = [variant(ch, copy, landing, campaign_id) for ch in CHANNELS]
    page = render_kit(shown, copy, brand, variants, landing, locale=locale, shelf=shelf)
    path = f"/k/{campaign_id}"
    ledger.upsert_campaign(campaign_id, {"kitHtml": page, "kitPath": path, "locale": locale})
    return {
        "autopost": False,
        "note": "Ready to upload. Owner makes the final click on their own channels.",
        "landing": landing,
        "kit": path,
        "themeId": resolve_theme(brand).id,
        "locale": locale,
        "storyHook": copy.get("storyHook"),
        "variants": variants,
        "assets": inka.get("assets") or {},
    }


def variant(channel: dict[str, Any], copy: dict[str, Any], landing: str, campaign_id: str) -> dict[str, Any]:
    headline = _clip(str(copy.get("headline") or ""), int(channel.get("headlineMax") or 40))
    primary = _clip(str(copy.get("primaryText") or copy.get("subhead") or ""), int(channel.get("primaryMax") or 125))
    cta = str(copy.get("cta") or "Learn more")
    loc_h = _clip(str(copy.get("headlineLocalized") or ""), int(channel.get("headlineMax") or 40))
    loc_p = _clip(str(copy.get("primaryTextLocalized") or ""), int(channel.get("primaryMax") or 125))
    loc_cta = str(copy.get("ctaLocalized") or "")
    if channel.get("aspect") == "9:16" and loc_h:
        headline, primary, cta = loc_h, loc_p or primary, loc_cta or cta
    utm = _utm(landing, campaign_id, channel["id"])
    lint = _lint(channel, f"{headline} {loc_h} {loc_p}", primary)
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
        "organic": bool(channel.get("organic")),
        "headlineLocalized": loc_h,
        "primaryTextLocalized": loc_p,
        "ctaLocalized": loc_cta,
        "voIndic": str(copy.get("voIndic") or ""),
        "voEn": str(copy.get("voEn") or ""),
        "charCounts": {
            "headline": len(headline),
            "primaryText": len(primary),
        },
    }
    if channel.get("stillSlot"):
        block["still"] = f"/media/{campaign_id}/{channel['stillSlot']}"
        block["stillSlot"] = channel["stillSlot"]
    if channel.get("clipSlot"):
        block["clip"] = f"/media/{campaign_id}/{channel['clipSlot']}"
        block["clipSlot"] = channel["clipSlot"]
    if channel.get("clipSlotEn"):
        block["clipEn"] = f"/media/{campaign_id}/{channel['clipSlotEn']}"
        block["clipSlotEn"] = channel["clipSlotEn"]
    if channel.get("proofClipSlot"):
        block["proofClip"] = f"/media/{campaign_id}/{channel['proofClipSlot']}"
        block["proofClipSlot"] = channel["proofClipSlot"]
    if channel.get("proofClipSlotEn"):
        block["proofClipEn"] = f"/media/{campaign_id}/{channel['proofClipSlotEn']}"
        block["proofClipSlotEn"] = channel["proofClipSlotEn"]
    box_key = {"4:5": "feed", "1:1": "square", "9:16": "story", "1.91:1": "landscape"}.get(str(channel.get("aspect") or ""))
    if box_key and box_key in PIXEL_BOXES:
        pw, ph, _a = PIXEL_BOXES[box_key]
        block["width"] = pw
        block["height"] = ph
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

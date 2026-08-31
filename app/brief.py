# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Turn a pasted URL into a campaign brief. Listing vs website — no scrape of Adshelf."""

from __future__ import annotations

import re
from typing import Any

_LISTING_MARKERS = (
    "share.google",
    "maps.google.",
    "google.com/maps",
    "maps.app.goo.gl",
    "goo.gl/maps",
)


def classify_url(url: str) -> str:
    """Return 'googleListing' for Maps / share.google links, else 'website'."""
    u = (url or "").strip().lower()
    if any(marker in u for marker in _LISTING_MARKERS):
        return "googleListing"
    return "website"


def split_asset_uris(raw: Any) -> list[str]:
    """Split a textarea, comma list, or JSON array into http(s) URIs."""
    if raw is None or raw == "":
        return []
    parts: list[str]
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, dict):
                parts.append(str(item.get("uri") or item.get("url") or ""))
            else:
                parts.append(str(item))
    else:
        parts = re.split(r"[\s,]+", str(raw))
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        uri = part.strip()
        if uri.startswith("http") and uri not in seen:
            seen.add(uri)
            out.append(uri[:500])
    return out


def normalize_brief(brief: dict[str, Any] | None) -> dict[str, Any]:
    """Classify `url` (or existing website / listing fields) and split extra asset URIs.

    Missing businessName becomes \"listing\" until Scout resolves a name.
    """
    out = dict(brief or {})
    url = str(out.pop("url", "") or "").strip()
    website = str(out.get("website") or out.get("site") or "").strip()
    listing = str(out.get("googleListing") or out.get("mapsUrl") or "").strip()

    if url:
        if classify_url(url) == "googleListing":
            out["googleListing"] = url
        else:
            out["website"] = url
    elif website and classify_url(website) == "googleListing" and not listing:
        out["googleListing"] = website
        if out.get("website") == website:
            out.pop("website", None)
        if out.get("site") == website:
            out.pop("site", None)
    elif listing and classify_url(listing) == "website" and not website:
        out["website"] = listing

    assets = split_asset_uris(out.get("assetUris") or out.get("assets") or out.get("photos"))
    if assets:
        out["assetUris"] = assets

    if not str(out.get("businessName") or "").strip():
        out["businessName"] = "listing"
    return out

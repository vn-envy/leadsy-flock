# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Domain-agnostic place vs proof objects. Same setup for a salon, kitchen, or clinic."""

from __future__ import annotations

from typing import Any

VERTICALS: dict[str, dict[str, str]] = {
    "salon": {
        "place": "empty styling station, bowls, warm light — this shop's room",
        "proof": "finished colour, cut, or the service on their menu card — not a generated client",
        "voHint": "the result, not the furniture",
    },
    "food": {
        "place": "dining room, pass, or counter — this kitchen's room",
        "proof": "the plated dish, thali, or drink from their menu photos",
        "voHint": "show the food, not only the tables",
    },
    "clinic": {
        "place": "chair, light, quiet treatment room",
        "proof": "a result they already published, or the treatment still-life from their gallery — never an invented patient",
        "voHint": "the outcome they already show, no medical claims",
    },
    "fitness": {
        "place": "floor, rack, morning light",
        "proof": "the session they can show without a fake body — class space or a result photo they supplied",
        "voHint": "the work, not a stock athlete",
    },
    "retail": {
        "place": "vitrine, shelf, or shop floor",
        "proof": "one SKU in macro from their own product shots",
        "voHint": "the piece you can buy",
    },
    "other": {
        "place": "this shop's interior",
        "proof": "the product or service artifact they actually sell",
        "voHint": "the thing a stranger must see to book",
    },
}

_ALIASES = {
    "beauty": "salon",
    "spa": "salon",
    "qsr": "food",
    "restaurant": "food",
    "cafe": "food",
    "café": "food",
    "bakery": "food",
    "dentist": "clinic",
    "dental": "clinic",
    "doctor": "clinic",
    "gym": "fitness",
    "jewellery": "retail",
    "jewelry": "retail",
    "boutique": "retail",
}

_PROOF_KINDS = {"menu", "pdf", "product"}
_PROOF_TOKS = (
    "menu",
    "dish",
    "food",
    "plate",
    "thali",
    "drink",
    "colour",
    "color",
    "result",
    "before",
    "after",
    "smile",
    "whitening",
    "product",
    "sku",
    "item",
    "work",
)
_PLACE_TOKS = (
    "interior",
    "storefront",
    "shop",
    "salon",
    "clinic",
    "gym",
    "dining",
    "room",
    "station",
    "listing",
    "maps",
    "facade",
    "façade",
)


def infer_vertical(blob: str, *, category: str = "") -> str:
    raw = f"{category} {blob}".lower()
    for key, dest in _ALIASES.items():
        if key in raw:
            return dest
    for key in VERTICALS:
        if key in raw:
            return key
    return "other"


def spec(vertical: str) -> dict[str, str]:
    return dict(VERTICALS.get(vertical) or VERTICALS["other"])


def infer_role(uri: str = "", kind: str = "", title: str = "") -> str:
    k = (kind or "").lower()
    if k in _PROOF_KINDS:
        return "proof"
    if k in {"listing", "maps", "website"}:
        return "place"
    blob = f"{uri} {title} {kind}".lower()
    if any(t in blob for t in _PROOF_TOKS):
        return "proof"
    if any(t in blob for t in _PLACE_TOKS):
        return "place"
    return "place"


def from_scout(scout: dict[str, Any] | None, brief: dict[str, Any] | None = None) -> dict[str, str]:
    scout = scout or {}
    brief = brief or {}
    cat = ""
    for row in scout.get("shelf") or []:
        if isinstance(row, dict) and row.get("category"):
            cat = str(row.get("category") or "")
            break
    named = str(scout.get("vertical") or brief.get("vertical") or "")
    vertical = infer_vertical(
        f"{named} {brief.get('businessName') or ''} {brief.get('goal') or ''} {brief.get('audience') or ''}",
        category=cat or named,
    )
    row = spec(vertical)
    proof = str(scout.get("proofObject") or row["proof"])
    return {"vertical": vertical, "proofObject": proof, **row}

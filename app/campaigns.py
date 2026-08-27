# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Campaign lifecycle used by both HTTP and Flo tools."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from app import ledger
from app.armor import ArmorBlocked, sanitize_user_prompt
from app.planner import recommend_flock
from app.pipeline import publish_step


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "campaign").lower()).strip("-")
    return slug[:40] or "campaign"


def _brief_blob(brief: dict[str, Any], raw_text: str) -> str:
    parts = [
        raw_text,
        str(brief.get("businessName") or ""),
        str(brief.get("geo") or ""),
        str(brief.get("goal") or ""),
        str(brief.get("audience") or ""),
    ]
    return " ".join(p for p in parts if p).strip()


def create_campaign(brief: dict[str, Any], *, raw_text: str = "") -> dict[str, Any]:
    blob = _brief_blob(brief, raw_text)
    if blob:
        sanitize_user_prompt(blob)
    campaign_id = f"{_slug(brief.get('businessName') or 'campaign')}-{uuid.uuid4().hex[:8]}"
    rec = recommend_flock(
        goal=str(brief.get("goal") or ""),
        budget_inr=_as_int(brief.get("budgetInr")),
        include_outreach=bool(brief.get("includeOutreach")),
    )
    ledger.upsert_campaign(
        campaign_id,
        {
            "status": "planned",
            "brief": brief,
            "engineConfig": rec,
            "rawText": raw_text[:2000],
        },
    )
    ledger.write_receipt(
        campaign_id=campaign_id,
        step="plan",
        engine="bri",
        status="ok",
        payload=rec,
    )
    ledger.write_event(
        campaign_id=campaign_id,
        kind="planned",
        detail={"hired": rec["hired"], "price_inr": rec["price_inr"]},
    )
    return {"id": campaign_id, "status": "planned", "brief": brief, "engineConfig": rec}


def approve_campaign(campaign_id: str) -> dict[str, Any]:
    campaign = ledger.get_campaign(campaign_id)
    if not campaign:
        raise KeyError(campaign_id)
    rec = campaign.get("engineConfig") or recommend_flock()
    pipeline = list(rec.get("pipeline") or ["scout"])
    first = pipeline[0]
    ledger.upsert_campaign(
        campaign_id,
        {
            "status": "running",
            "approvedAt": ledger.now_iso(),
            "currentStep": first,
        },
    )
    ledger.write_receipt(
        campaign_id=campaign_id,
        step="approve",
        engine="flo",
        status="ok",
        payload={"pipeline": pipeline},
    )
    message_id = publish_step(campaign_id=campaign_id, step=first, pipeline=pipeline)
    return {
        "id": campaign_id,
        "status": "running",
        "pipeline": pipeline,
        "publishedStep": first,
        "pubsubMessageId": message_id,
    }


def campaign_view(campaign_id: str) -> dict[str, Any] | None:
    campaign = ledger.get_campaign(campaign_id)
    if not campaign:
        return None
    campaign["receipts"] = ledger.list_receipts(campaign_id)
    return campaign


def screen_text(text: str) -> dict[str, Any]:
    try:
        verdict = sanitize_user_prompt(text)
        return {"allowed": True, "verdict": verdict}
    except ArmorBlocked as exc:
        return {"allowed": False, "verdict": exc.verdict}


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def decode_pubsub_push(body: dict[str, Any]) -> dict[str, Any]:
    message = body.get("message") or {}
    data = message.get("data") or ""
    if not data:
        raise ValueError("missing pubsub data")
    import base64

    raw = base64.b64decode(data).decode("utf-8")
    payload = json.loads(raw)
    payload["messageId"] = message.get("messageId") or message.get("message_id")
    return payload

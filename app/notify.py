# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Owner Telegram pings + founder-alerts. Never email, call, or autopost."""

from __future__ import annotations

import json
import os
from typing import Any

from app import ledger
from app.settings import load_settings


def after_step(campaign_id: str, step: str, result: dict[str, Any] | None = None, campaign: dict[str, Any] | None = None) -> None:
    if step not in {"scout", "ad_kit"}:
        return
    if not isinstance(campaign, dict):
        fetched = ledger.get_campaign(campaign_id)
        campaign = fetched if isinstance(fetched, dict) else None
    if not isinstance(campaign, dict):
        return
    chat_id = campaign.get("telegramChatId")
    if not _real_id(chat_id):
        return
    if step == "scout":
        name = (result or {}).get("resolvedName") or (campaign.get("brief") or {}).get("businessName") or campaign_id
        _telegram(
            chat_id,
            f"Scout locked *{name}*. Films next — same chat, no disappearing until Friday.",
        )
        _alert("scout_ok", campaign_id, {"resolvedName": name})
        return
    if step == "ad_kit":
        ping_kit_ready(campaign_id, campaign)


def ping_kit_ready(campaign_id: str, campaign: dict[str, Any] | None = None) -> None:
    campaign = campaign or ledger.get_campaign(campaign_id) or {}
    if not isinstance(campaign, dict):
        return
    chat_id = campaign.get("telegramChatId")
    if not _real_id(chat_id):
        _alert("kit_ready", campaign_id, {"telegram": False})
        return
    base = _app_url()
    studio = _studio_url(campaign_id, campaign, base)
    kit = f"{base}/k/{campaign_id}"
    landing = f"{base}/l/{campaign_id}"
    _telegram(
        chat_id,
        "Kit is on a URL. This is the delivery room — we do not autopost.\n\n"
        f"Studio (keep this): {studio}\n"
        f"Paste kit: {kit}\n"
        f"Consent landing: {landing}\n\n"
        "Paste into your own Ads Manager. Reply /status any time.",
    )
    _alert("kit_ready", campaign_id, {"studio": True, "kit": kit})


def ping_approved(campaign_id: str, chat_id: Any) -> None:
    if not _real_id(chat_id):
        return
    _telegram(
        chat_id,
        f"Approved. The flock is working in the background.\nCampaign `{campaign_id}`.\n"
        "I'll ping this chat when the studio URL is live. No autopost.",
    )


def _studio_url(campaign_id: str, campaign: dict[str, Any], base: str) -> str:
    key = campaign.get("studioKey") or ""
    if key:
        return f"{base}/s/{campaign_id}?k={key}"
    return f"{base}/s/{campaign_id}"


def _app_url() -> str:
    return (os.environ.get("APP_URL") or "https://flock-api-533880600838.asia-south1.run.app").rstrip("/")


def _telegram(chat_id: Any, text: str) -> None:
    from app.telegram_adapter import send_message

    send_message(chat_id, text)


def _alert(kind: str, campaign_id: str, detail: dict[str, Any]) -> None:
    try:
        from app.pipeline import publisher

        s = load_settings()
        if not s.project_id:
            return
        topic = f"projects/{s.project_id}/topics/{s.alerts_topic}"
        body = json.dumps(
            {"kind": kind, "campaignId": campaign_id, "detail": detail, "at": ledger.now_iso()}
        ).encode("utf-8")
        publisher().publish(topic, body, kind=kind, campaignId=campaign_id)
    except Exception:  # noqa: BLE001 — alerts must never fail a campaign step
        return


def _real_id(value: Any) -> bool:
    return isinstance(value, int) or (isinstance(value, str) and value.strip().lstrip("-").isdigit())

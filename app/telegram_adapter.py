# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Thin Telegram adapter. Flo-grade: screen, brief, plan, approve. No old-bot code."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from app.armor import ArmorBlocked
from app.campaigns import approve_campaign, create_campaign
from app import ledger

_CHAT_COL = "telegramChats"


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def handle_update(update: dict[str, Any]) -> dict[str, Any]:
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return {"ok": True, "ignored": True}
    if not text:
        _send(chat_id, "Send a text brief — Flo reads messages, not files yet.")
        return {"ok": True}
    if text.lower() in {"/start", "hi", "hello"}:
        _send(
            chat_id,
            "Flo here. Tell me the business, city, and what success looks like. "
            "Example: FitNorth gym, Sector 56 Gurgaon, 50 evening members.",
        )
        return {"ok": True, "greeted": True}
    if text.lower() in {"yes", "approve", "go", "/approve"}:
        cid = _last_campaign(chat_id)
        if not cid:
            _send(chat_id, "No plan waiting. Send a brief first.")
            return {"ok": True}
        try:
            result = approve_campaign(cid)
        except KeyError:
            _send(chat_id, "That campaign vanished. Send the brief again.")
            return {"ok": True}
        _send(
            chat_id,
            f"Approved. The flock is working in the background.\nCampaign `{result['id']}` · first step {result['publishedStep']}",
        )
        return {"ok": True, "approved": cid}
    try:
        created = create_campaign(
            {
                "businessName": _guess_name(text),
                "geo": "",
                "goal": text,
            },
            raw_text=text,
        )
    except ArmorBlocked:
        _send(chat_id, "I can't take that brief. Rephrase without the blocked content.")
        return {"ok": True, "blocked": True}
    _remember(chat_id, created["id"])
    rec = created.get("engineConfig") or {}
    hired = ", ".join(rec.get("hired") or [])
    price = rec.get("price_inr")
    _send(
        chat_id,
        f"Plan `{created['id']}`\nHired: {hired or 'core flock'}\nPrice: ₹{price}\nReply YES to approve.",
    )
    return {"ok": True, "campaignId": created["id"]}


def _guess_name(text: str) -> str:
    words = text.replace(",", " ").split()
    return " ".join(words[:3])[:40] or "campaign"


def _remember(chat_id: Any, campaign_id: str) -> None:
    db = ledger.client()
    db.collection(_CHAT_COL).document(str(chat_id)).set(
        {"campaignId": campaign_id, "updatedAt": ledger.now_iso()},
        merge=True,
    )


def _last_campaign(chat_id: Any) -> str | None:
    db = ledger.client()
    snap = db.collection(_CHAT_COL).document(str(chat_id)).get()
    if not snap.exists:
        return None
    return (snap.to_dict() or {}).get("campaignId")


def _send(chat_id: Any, text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()

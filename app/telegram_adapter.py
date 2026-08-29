# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Telegram is the meeting. Same ADK Flo as /run_sse. DM only. No old-bot code."""

from __future__ import annotations

import hmac
import inspect
import json
import logging
import os
import urllib.request
from typing import Any

from app import channel, ledger
from app.armor import ArmorBlocked
from app.campaigns import approve_campaign, create_campaign

log = logging.getLogger("leadsy.telegram")

_CHAT_COL = "telegramChats"
_MAX_TG = 3900


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def webhook_secret() -> str:
    return (os.environ.get("TELEGRAM_WEBHOOK_SECRET") or "").strip()


def verify_webhook_secret(header: str | None) -> bool:
    expected = webhook_secret()
    if not expected:
        return True
    return hmac.compare_digest(header or "", expected)


def allowlist() -> set[str]:
    raw = os.environ.get("TELEGRAM_ALLOW_USER_IDS") or ""
    return {part.strip() for part in raw.split(",") if part.strip()}


def send_message(chat_id: Any, text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or chat_id is None:
        return
    body = (text or "").strip()
    if len(body) > _MAX_TG:
        body = body[: _MAX_TG - 1] + "…"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {"chat_id": chat_id, "text": body, "disable_web_page_preview": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("telegram send failed: %s", exc)


async def handle_update(update: dict[str, Any], *, runner: Any = None) -> dict[str, Any]:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = from_user.get("id")
    chat_type = str(chat.get("type") or "")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return {"ok": True, "ignored": True}
    if chat_type and chat_type != "private":
        send_message(chat_id, "Flo only takes briefs in a private chat.")
        return {"ok": True, "ignored": "group"}
    allowed = allowlist()
    if allowed and str(user_id) not in allowed:
        send_message(chat_id, "This bot is private. Ask Neekhil for access.")
        return {"ok": True, "denied": True}
    if not text:
        send_message(chat_id, "Send a text brief — Flo reads messages, not files yet.")
        return {"ok": True}
    lowered = text.lower().strip()
    if lowered in {"/start", "hi", "hello", "/help"}:
        send_message(chat_id, _GREET)
        return {"ok": True, "greeted": True}
    if lowered in {"/status", "status"}:
        return _status(chat_id)
    if lowered in {"yes", "approve", "go", "/approve"}:
        return _approve(chat_id)

    ctx = channel.ChannelCtx(source="telegram", chat_id=chat_id, user_id=user_id)
    token = channel.bind(ctx)
    try:
        if runner is None:
            created = _brief_without_flo(text)
            remember(chat_id, created["id"])
            rec = created.get("engineConfig") or {}
            hired = ", ".join(rec.get("hired") or [])
            send_message(
                chat_id,
                f"Plan `{created['id']}`\nHired: {hired or 'core flock'}\n"
                f"Price: ₹{rec.get('price_inr')}\nReply YES to approve.\n"
                "(Flo ADK was offline for this turn — plan still catalog-backed.)",
            )
            return {"ok": True, "campaignId": created["id"], "flo": False}
        reply = await ask_flo(runner, user_id=user_id, chat_id=chat_id, text=text)
        if ctx.campaign_id:
            remember(chat_id, ctx.campaign_id)
            ledger.upsert_campaign(
                ctx.campaign_id,
                {"telegramChatId": chat_id, "telegramUserId": user_id},
            )
        send_message(chat_id, reply)
        return {"ok": True, "campaignId": ctx.campaign_id, "flo": True}
    except ArmorBlocked:
        send_message(chat_id, "I can't take that brief. Rephrase without the blocked content.")
        return {"ok": True, "blocked": True}
    finally:
        channel.reset(token)


async def ask_flo(runner: Any, *, user_id: Any, chat_id: Any, text: str) -> str:
    from google.genai import types

    from app.agent import app as adk_app

    uid = f"tg:{user_id}"
    sid = f"tg-chat-{chat_id}"
    await _ensure_session(runner, adk_app.name, uid, sid)
    content = types.Content(role="user", parts=[types.Part.from_text(text=text)])
    texts: list[str] = []
    async for event in runner.run_async(user_id=uid, session_id=sid, new_message=content):
        if not getattr(event, "is_final_response", lambda: False)():
            continue
        body = getattr(event, "content", None)
        for part in getattr(body, "parts", None) or []:
            piece = getattr(part, "text", None)
            if piece:
                texts.append(piece)
    return "\n".join(texts).strip() or "Flo went quiet. Send that again in a moment."


async def _ensure_session(runner: Any, app_name: str, user_id: str, session_id: str) -> None:
    svc = getattr(runner, "session_service", None)
    if svc is None:
        return
    existing = await _maybe_await(
        svc.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    )
    if existing:
        return
    await _maybe_await(
        svc.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    )


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _approve(chat_id: Any) -> dict[str, Any]:
    cid = last_campaign(chat_id)
    if not cid:
        send_message(chat_id, "No plan waiting. Send a brief first.")
        return {"ok": True}
    campaign = ledger.get_campaign(cid) or {}
    if campaign.get("status") in {"running", "completed"}:
        send_message(chat_id, f"`{cid}` is already {campaign.get('status')}. /status for the studio URL.")
        return {"ok": True, "already": cid}
    try:
        result = approve_campaign(cid)
    except KeyError:
        send_message(chat_id, "That campaign vanished. Send the brief again.")
        return {"ok": True}
    from app.notify import ping_approved

    ping_approved(cid, chat_id)
    return {"ok": True, "approved": cid, "publishedStep": result.get("publishedStep")}


def _status(chat_id: Any) -> dict[str, Any]:
    cid = last_campaign(chat_id)
    if not cid:
        send_message(chat_id, "No campaign in this chat yet. Send a brief.")
        return {"ok": True}
    campaign = ledger.get_campaign(cid) or {}
    status = campaign.get("status") or "unknown"
    name = (campaign.get("brief") or {}).get("businessName") or cid
    base = (os.environ.get("APP_URL") or "").rstrip("/")
    bits = [f"{name} · `{cid}` · {status}"]
    key = campaign.get("studioKey") or ""
    if base and key:
        bits.append(f"Studio: {base}/s/{cid}?k={key}")
    if campaign.get("kitPath") and base:
        bits.append(f"Kit: {base}{campaign['kitPath']}")
    if campaign.get("landingPath") and base:
        bits.append(f"Landing: {base}{campaign['landingPath']}")
    bits.append("We do not autopost.")
    send_message(chat_id, "\n".join(bits))
    return {"ok": True, "campaignId": cid, "status": status}


def _brief_without_flo(text: str) -> dict[str, Any]:
    words = text.replace(",", " ").split()
    name = " ".join(words[:3])[:40] or "campaign"
    return create_campaign({"businessName": name, "geo": "", "goal": text}, raw_text=text)


def remember(chat_id: Any, campaign_id: str) -> None:
    db = ledger.client()
    db.collection(_CHAT_COL).document(str(chat_id)).set(
        {"campaignId": campaign_id, "updatedAt": ledger.now_iso()},
        merge=True,
    )


def last_campaign(chat_id: Any) -> str | None:
    db = ledger.client()
    snap = db.collection(_CHAT_COL).document(str(chat_id)).get()
    if not snap.exists:
        return None
    return (snap.to_dict() or {}).get("campaignId")


_GREET = (
    "Flo here. Brief me like a local agency — business, city, what success looks like. "
    "Example: Mira's Chai, Koramangala Bangalore, evening takeaway cups.\n\n"
    "I hire the flock and quote rupees. Reply YES to approve. "
    "When the kit is ready you get a studio URL. We never autopost.\n\n"
    "/approve · /status"
)

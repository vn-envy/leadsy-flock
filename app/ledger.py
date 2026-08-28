# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Firestore receipts ledger. Pre-write the audit row, then act."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from google.cloud import firestore

from app.settings import load_settings

COL_CAMPAIGNS = "campaigns"
COL_RECEIPTS = "receipts"
COL_EVENTS = "agentEvents"
COL_MEMORIES = "memories"
COL_CONSENTS = "consents"
COL_ASSETS = "assets"


def client() -> firestore.Client:
    settings = load_settings()
    database = settings.firestore_database or "(default)"
    return firestore.Client(
        project=settings.project_id or None,
        database=database,
    )


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


_DONE_STATUSES = {"ok", "skip", "blocked"}


def merge_receipt(prev: dict[str, Any] | None, body: dict[str, Any]) -> dict[str, Any]:
    """Firestore merge is shallow: a started write with {idempotencyKey} would
    replace a finished engine payload. Never regress a done receipt to started."""
    incoming = dict(body)
    incoming_payload = dict(incoming.get("payload") or {})
    if not prev:
        out = dict(incoming)
        out.setdefault("createdAt", incoming.get("updatedAt"))
        out["payload"] = incoming_payload
        return out
    prev_payload = dict(prev.get("payload") or {})
    if incoming.get("status") == "started" and prev.get("status") in _DONE_STATUSES:
        out = dict(incoming)
        out["status"] = prev.get("status")
        out["payload"] = prev_payload
        return out
    out = dict(incoming)
    if incoming.get("status") == "started":
        out["payload"] = {**prev_payload, **incoming_payload}
    elif incoming_payload:
        out["payload"] = incoming_payload
    else:
        out["payload"] = prev_payload
    return out


def write_receipt(
    *,
    campaign_id: str,
    step: str,
    engine: str,
    status: str,
    payload: dict[str, Any] | None = None,
    legal_basis: str = "owner_instruction",
    attempt: int = 1,
    db: firestore.Client | None = None,
) -> str:
    db = db or client()
    receipt_id = f"{campaign_id}_{step}"
    body = {
        "campaignId": campaign_id,
        "step": step,
        "engine": engine,
        "status": status,
        "attempt": attempt,
        "legalBasis": legal_basis,
        "payload": payload or {},
        "updatedAt": now_iso(),
        "project": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "service": os.environ.get("K_SERVICE", "local"),
    }
    ref = db.collection(COL_RECEIPTS).document(receipt_id)
    snap = ref.get()
    prev = snap.to_dict() if snap.exists else None
    merged = merge_receipt(prev, body)
    if prev is None:
        ref.set(merged)
    else:
        ref.set(merged, merge=True)
    return receipt_id


def get_receipt(campaign_id: str, step: str, db: firestore.Client | None = None) -> dict | None:
    db = db or client()
    snap = db.collection(COL_RECEIPTS).document(f"{campaign_id}_{step}").get()
    return snap.to_dict() if snap.exists else None


def upsert_campaign(campaign_id: str, data: dict[str, Any], db: firestore.Client | None = None) -> None:
    db = db or client()
    payload = {**data, "updatedAt": now_iso()}
    if "createdAt" not in payload:
        payload.setdefault("createdAt", payload["updatedAt"])
    db.collection(COL_CAMPAIGNS).document(campaign_id).set(payload, merge=True)


def get_campaign(campaign_id: str, db: firestore.Client | None = None) -> dict | None:
    db = db or client()
    snap = db.collection(COL_CAMPAIGNS).document(campaign_id).get()
    if not snap.exists:
        return None
    body = snap.to_dict() or {}
    body["id"] = campaign_id
    return body


def list_receipts(campaign_id: str, db: firestore.Client | None = None) -> list[dict]:
    db = db or client()
    docs = (
        db.collection(COL_RECEIPTS)
        .where("campaignId", "==", campaign_id)
        .stream()
    )
    rows = []
    for doc in docs:
        row = doc.to_dict() or {}
        row["id"] = doc.id
        rows.append(row)
    rows.sort(key=lambda r: r.get("createdAt") or r.get("updatedAt") or "")
    return rows


def list_campaigns(limit: int = 40, db: firestore.Client | None = None) -> list[dict]:
    db = db or client()
    rows = []
    for doc in db.collection(COL_CAMPAIGNS).limit(limit).stream():
        row = doc.to_dict() or {}
        row["id"] = doc.id
        rows.append(row)
    rows.sort(key=lambda r: r.get("updatedAt") or r.get("createdAt") or "", reverse=True)
    return rows


def write_memory(
    campaign_id: str,
    *,
    kind: str,
    text: str,
    db: firestore.Client | None = None,
) -> str:
    db = db or client()
    _, ref = db.collection(COL_MEMORIES).add(
        {
            "campaignId": campaign_id,
            "kind": kind,
            "text": text,
            "createdAt": now_iso(),
        }
    )
    return ref.id


def list_memories(campaign_id: str, kind: str | None = None, db: firestore.Client | None = None) -> list[dict]:
    db = db or client()
    query = db.collection(COL_MEMORIES).where("campaignId", "==", campaign_id)
    rows = []
    for doc in query.stream():
        row = doc.to_dict() or {}
        if kind and row.get("kind") != kind:
            continue
        row["id"] = doc.id
        rows.append(row)
    return rows


def write_consent(
    campaign_id: str,
    *,
    name: str,
    contact: str,
    source: str = "landing",
    db: firestore.Client | None = None,
) -> str:
    db = db or client()
    _, ref = db.collection(COL_CONSENTS).add(
        {
            "campaignId": campaign_id,
            "name": name,
            "contact": contact,
            "source": source,
            "createdAt": now_iso(),
        }
    )
    return ref.id


def list_consents(campaign_id: str, db: firestore.Client | None = None) -> list[dict]:
    db = db or client()
    rows = []
    for doc in db.collection(COL_CONSENTS).where("campaignId", "==", campaign_id).stream():
        row = doc.to_dict() or {}
        row["id"] = doc.id
        rows.append(row)
    return rows


def write_event(
    *,
    campaign_id: str,
    kind: str,
    detail: dict[str, Any],
    db: firestore.Client | None = None,
) -> None:
    db = db or client()
    db.collection(COL_EVENTS).add(
        {
            "campaignId": campaign_id,
            "kind": kind,
            "detail": detail,
            "createdAt": now_iso(),
        }
    )

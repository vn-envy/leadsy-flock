# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Outreach gate + Ray sandbox. No consent → refuse. Never cold-email."""

from __future__ import annotations

from typing import Any

from app import ledger


def run_gate(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    consents = ledger.list_consents(campaign_id)
    if not consents:
        return {
            "verdict": "refuse",
            "reason": "no consent record",
            "rule": "discovery_ne_consent",
        }
    return {
        "verdict": "pass",
        "reason": f"{len(consents)} consent record(s)",
        "rule": "discovery_ne_consent",
        "consentIds": [c.get("id") for c in consents[:10]],
    }


def run_ray(campaign: dict[str, Any]) -> dict[str, Any]:
    """Sandbox only: write an outbox row. Do not send SMTP or Gmail."""
    gate = (ledger.get_receipt(campaign.get("id") or "", "outreach_gate") or {}).get("payload") or {}
    if gate.get("verdict") != "pass":
        return {"sent": False, "reason": "outreach_gate_refused", "sandbox": True}
    consents = ledger.list_consents(campaign.get("id") or "")
    written = []
    for row in consents[:5]:
        body = {
            "to": row.get("contact"),
            "subject": "Thanks for opting in",
            "preview": "Sandbox — this was not delivered to a real inbox.",
            "consentId": row.get("id"),
        }
        ledger.write_event(
            campaign_id=campaign.get("id") or "",
            kind="sandbox_email",
            detail=body,
        )
        written.append(body["consentId"])
    return {"sent": False, "sandbox": True, "outbox": written}

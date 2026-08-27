# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Creative Gate — Ledge. Regex + Gemma classifier + Gemini judge. Fail-closed."""

from __future__ import annotations

import re
from typing import Any

from google.genai import types

from app import ledger
from app.engines import gemini_util as g

BANNED = [
    (r"\bguaranteed?\b", "guaranteed_outcome"),
    (r"\bmiracle\b", "miracle_claim"),
    (r"\bcure(s|d)?\b", "medical_claim"),
    (r"\b100\s*%\b", "absolute_claim"),
    (r"\bno risk\b", "no_risk"),
    (r"\bsix[- ]pack in\b", "body_guarantee"),
    (r"\bclinically proven\b", "clinical_claim"),
]


def banned_hits(text: str) -> list[str]:
    found: list[str] = []
    blob = text or ""
    for pattern, label in BANNED:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            found.append(label)
    return found


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    copy = inka.get("copy") or {}
    draft = str(copy.get("draftHeadline") or "")
    headline = str(copy.get("headline") or "")
    primary = str(copy.get("primaryText") or "")
    draft_hits = banned_hits(draft)
    final_hits = banned_hits(f"{headline}\n{primary}")

    gemma = _gemma_classify(f"{headline}\n{primary}")
    judge = _gemini_judge(headline, primary, final_hits)

    draft_rejected = bool(draft_hits)
    final_blocked = bool(final_hits) or gemma.get("risk") == "high" or judge.get("verdict") == "reject"
    if final_blocked:
        ledger.write_memory(
            campaign_id,
            kind="policy",
            text=(
                "Creative Gate rejected outcome/medical/absolute claims. "
                f"labels={final_hits or gemma.get('labels')}. Rewrite without guarantees."
            ),
        )
        verdict = "reject"
    else:
        verdict = "pass"
        if draft_rejected:
            ledger.write_memory(
                campaign_id,
                kind="policy",
                text=f"Rejected internal draft claims: {draft_hits}. Passed compliant headline.",
            )

    return {
        "verdict": verdict,
        "draft": {"text": draft, "hits": draft_hits, "rejected": draft_rejected},
        "final": {"text": headline, "hits": final_hits},
        "classifier": gemma,
        "judge": judge,
        "rule": "fail_closed_claims",
    }


def _gemma_classify(text: str) -> dict[str, Any]:
    prompt = (
        "You are a claims classifier for Indian advertising. "
        "Reply ONLY JSON {\"risk\":\"low\"|\"high\",\"labels\":[\"...\"]}. "
        "high = guaranteed results, medical cure, miracle, 100% claims.\n\n"
        f"COPY:\n{text}"
    )
    try:
        client = g.media_client()
        resp = client.models.generate_content(
            model=g.GEMMA_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        parsed = g.extract_json(g.response_text(resp))
        parsed["model"] = g.GEMMA_MODEL
        parsed["ok"] = True
        return parsed
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "model": g.GEMMA_MODEL, "error": str(exc)[:300], "risk": "unknown"}


def _gemini_judge(headline: str, primary: str, hits: list[str]) -> dict[str, Any]:
    prompt = (
        "You are Ledge, the auditor. Decide if this ad copy may run for a local gym/SMB in India. "
        "Refuse guaranteed outcomes, medical claims, and invented testimonials. "
        "Return ONLY JSON {\"verdict\":\"pass\"|\"reject\",\"reason\":\"...\"}.\n\n"
        f"HEADLINE: {headline}\nPRIMARY: {primary}\nREGEX_HITS: {hits}"
    )
    try:
        client = g.text_client()
        resp = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        parsed = g.extract_json(g.response_text(resp))
        parsed["model"] = g.TEXT_MODEL
        parsed["ok"] = True
        if hits:
            parsed["verdict"] = "reject"
            parsed["reason"] = parsed.get("reason") or f"regex hits: {hits}"
        return parsed
    except Exception as exc:  # noqa: BLE001
        if hits:
            return {"ok": False, "verdict": "reject", "reason": f"judge_error_fail_closed:{exc}"[:300], "model": g.TEXT_MODEL}
        return {"ok": False, "verdict": "pass", "reason": "judge unavailable; regex clean", "model": g.TEXT_MODEL}

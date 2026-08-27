# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Engine-step worker. Each Pub/Sub message is one step; receipts first, then act."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from app import ledger
from app.pipeline import publish_next

tracer = trace.get_tracer("leadsy.flock.worker")

ENGINE_FOR_STEP = {
    "scout": "scout",
    "inka": "inka",
    "creative_gate": "ledge",
    "stella": "stella",
    "ad_kit": "inka",
    "outreach_gate": "ledge",
}


def handle_step(message: dict[str, Any]) -> dict[str, Any]:
    campaign_id = message["campaignId"]
    step = message["step"]
    pipeline = list(message.get("pipeline") or [])
    attempt = int(message.get("attempt") or 1)
    engine = ENGINE_FOR_STEP.get(step, step)

    existing = ledger.get_receipt(campaign_id, step)
    if existing and existing.get("status") == "ok":
        nxt = publish_next(campaign_id, step, pipeline)
        return {"status": "already_done", "campaignId": campaign_id, "step": step, "next": nxt}

    ledger.write_receipt(
        campaign_id=campaign_id,
        step=step,
        engine=engine,
        status="started",
        attempt=attempt,
        payload={"idempotencyKey": message.get("idempotencyKey")},
    )

    with tracer.start_as_current_span(f"engine.{step}") as span:
        span.set_attribute("campaign.id", campaign_id)
        span.set_attribute("engine.step", step)
        span.set_attribute("engine.name", engine)
        span.set_attribute("engine.attempt", attempt)
        result = _run_step(step, campaign_id)
        span.set_attribute("engine.status", "ok")

    ledger.write_receipt(
        campaign_id=campaign_id,
        step=step,
        engine=engine,
        status="ok",
        attempt=attempt,
        payload=result,
    )
    ledger.write_event(
        campaign_id=campaign_id,
        kind="step_ok",
        detail={"step": step, "engine": engine},
    )
    nxt = publish_next(campaign_id, step, pipeline)
    if nxt is None:
        ledger.upsert_campaign(campaign_id, {"status": "completed"})
    else:
        ledger.upsert_campaign(campaign_id, {"status": "running", "currentStep": _next_name(step, pipeline)})
    return {
        "status": "ok",
        "campaignId": campaign_id,
        "step": step,
        "nextMessageId": nxt,
        "result": result,
    }


def _next_name(current: str, pipeline: list[str]) -> str | None:
    try:
        idx = pipeline.index(current)
    except ValueError:
        return None
    if idx + 1 >= len(pipeline):
        return None
    return pipeline[idx + 1]


def _run_step(step: str, campaign_id: str) -> dict[str, Any]:
    """Infra skeleton: each engine records a typed artifact. Real Scout/Inka land next."""
    campaign = ledger.get_campaign(campaign_id) or {}
    brief = campaign.get("brief") or {}
    if step == "scout":
        return {
            "evidence": [
                {
                    "source": "infra-skeleton",
                    "note": "Maps/Search/urlContext + crowd lens not run yet; receipt proves the hop.",
                    "business": brief.get("businessName"),
                    "geo": brief.get("geo"),
                }
            ]
        }
    if step == "inka":
        return {"artifact": "master-creative-pending", "models": ["gemini-2.5-flash-image", "veo-3.1-generate-001", "lyria-002"]}
    if step == "creative_gate":
        return {"verdict": "pass", "classifier": "gemma3", "judge": "gemini-3.5-flash", "note": "skeleton pass; live Gemma gate is next"}
    if step == "stella":
        return {"landing": "pending", "consentCapture": True}
    if step == "ad_kit":
        return {"kit": "pending", "channels": ["meta", "google"], "autopost": False}
    if step == "outreach_gate":
        return {"verdict": "refuse", "reason": "no consent record", "rule": "discovery_ne_consent"}
    return {"note": f"unknown step {step} recorded"}

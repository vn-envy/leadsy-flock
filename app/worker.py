# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Engine-step worker. Each Pub/Sub message is one step; receipts first, then act."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from app import ledger
from app.engines import dispatch
from app.pipeline import publish_next, publish_step

tracer = trace.get_tracer("leadsy.flock.worker")

ENGINE_FOR_STEP = {
    "scout": "scout",
    "inka": "inka",
    "creative_gate": "ledge",
    "stella": "stella",
    "ad_kit": "inka",
    "outreach_gate": "ledge",
    "ray": "ray",
}


def handle_step(message: dict[str, Any]) -> dict[str, Any]:
    campaign_id = message["campaignId"]
    step = message["step"]
    pipeline = list(message.get("pipeline") or [])
    attempt = int(message.get("attempt") or 1)
    engine = ENGINE_FOR_STEP.get(step, step)
    force = bool(message.get("forceRetry"))

    existing = ledger.get_receipt(campaign_id, step)
    if existing and existing.get("status") == "ok" and not force:
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
        result = run_engine(step, campaign_id)
        span.set_attribute("engine.status", result.get("verdict") or "ok")

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
        detail={"step": step, "engine": engine, "verdict": result.get("verdict")},
    )

    if step == "creative_gate" and result.get("verdict") == "reject":
        return _revise_or_block(campaign_id, pipeline, result)

    nxt = publish_next(campaign_id, step, pipeline)
    if nxt is None:
        ledger.upsert_campaign(campaign_id, {"status": "completed"})
    else:
        ledger.upsert_campaign(
            campaign_id,
            {"status": "running", "currentStep": _next_name(step, pipeline)},
        )
    return {
        "status": "ok",
        "campaignId": campaign_id,
        "step": step,
        "nextMessageId": nxt,
        "result": result,
    }


def run_engine(step: str, campaign_id: str) -> dict[str, Any]:
    campaign = ledger.get_campaign(campaign_id) or {}
    campaign["id"] = campaign_id
    return dispatch(step, campaign)


def _revise_or_block(campaign_id: str, pipeline: list[str], result: dict[str, Any]) -> dict[str, Any]:
    campaign = ledger.get_campaign(campaign_id) or {}
    revisions = int(campaign.get("inkaRevisions") or 1)
    if revisions < 2:
        ledger.upsert_campaign(
            campaign_id,
            {"status": "revising", "inkaRevisions": revisions + 1, "currentStep": "inka"},
        )
        nxt = publish_step(
            campaign_id=campaign_id,
            step="inka",
            pipeline=pipeline,
            attempt=revisions + 1,
            force_retry=True,
        )
        return {
            "status": "revise",
            "campaignId": campaign_id,
            "step": "creative_gate",
            "nextMessageId": nxt,
            "result": result,
        }
    ledger.upsert_campaign(campaign_id, {"status": "blocked_creative"})
    return {
        "status": "blocked",
        "campaignId": campaign_id,
        "step": "creative_gate",
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

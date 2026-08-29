# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Engine-step worker. Each Pub/Sub message is one step; receipts first, then act."""

from __future__ import annotations

import os
import time
from typing import Any

from opentelemetry import trace

from app import ledger
from app.engines import dispatch
from app.pipeline import publish_next, publish_step

tracer = trace.get_tracer("leadsy.flock.worker")

ENGINE_FOR_STEP = {
    "scout": "scout",
    "inka": "inka",
    "inka_harvest": "inka",
    "creative_gate": "ledge",
    "stella": "stella",
    "ad_kit": "inka",
    "outreach_gate": "ledge",
    "ray": "ray",
}

SIDECAR_STEPS = {"inka_harvest"}
HARVEST_MAX_ATTEMPTS = int(os.environ.get("HARVEST_MAX_ATTEMPTS", "24"))
HARVEST_POLL_SECONDS = int(os.environ.get("HARVEST_POLL_SECONDS", "12"))


def handle_step(message: dict[str, Any]) -> dict[str, Any]:
    campaign_id = message["campaignId"]
    step = message["step"]
    pipeline = list(message.get("pipeline") or [])
    attempt = int(message.get("attempt") or 1)
    engine = ENGINE_FOR_STEP.get(step, step)
    force = bool(message.get("forceRetry"))

    existing = ledger.get_receipt(campaign_id, step)
    if existing and existing.get("status") == "ok" and not force:
        nxt = None
        if step not in SIDECAR_STEPS:
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
        try:
            result = run_engine(step, campaign_id, attempt=attempt)
        except Exception as exc:  # noqa: BLE001 — ACK the push; do not 500-loop Pub/Sub
            result = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
        span.set_attribute("engine.status", result.get("verdict") or result.get("ok") or "ok")

    receipt_status = "polling" if step in SIDECAR_STEPS and result.get("retry") else "ok"
    if (
        step == "scout"
        and existing
        and existing.get("status") == "ok"
        and (existing.get("payload") or {}).get("resolvedName")
        and not result.get("resolvedName")
    ):
        # A JSON-failed Scout retry must not erase a listing we already resolved.
        result = dict(existing.get("payload") or {})
        result.setdefault("errors", [])
        if isinstance(result["errors"], list):
            result["errors"] = [*result["errors"], "kept_previous_resolvedName"]
        receipt_status = "ok"
    ledger.write_receipt(
        campaign_id=campaign_id,
        step=step,
        engine=engine,
        status=receipt_status,
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

    if step == "inka":
        _maybe_start_harvest(campaign_id, pipeline, result)

    if step in SIDECAR_STEPS:
        if result.get("retry") and attempt < HARVEST_MAX_ATTEMPTS:
            time.sleep(HARVEST_POLL_SECONDS)
            nxt = publish_step(
                campaign_id=campaign_id,
                step="inka_harvest",
                pipeline=pipeline,
                attempt=attempt + 1,
                force_retry=True,
            )
            return {
                "status": "polling",
                "campaignId": campaign_id,
                "step": step,
                "nextMessageId": nxt,
                "result": result,
            }
        _after_step(campaign_id, step, result)
        return {"status": "ok", "campaignId": campaign_id, "step": step, "result": result}

    nxt = publish_next(campaign_id, step, pipeline)
    if nxt is None:
        ledger.upsert_campaign(campaign_id, {"status": "completed"})
    else:
        ledger.upsert_campaign(
            campaign_id,
            {"status": "running", "currentStep": _next_name(step, pipeline)},
        )
    _after_step(campaign_id, step, result)
    return {
        "status": "ok",
        "campaignId": campaign_id,
        "step": step,
        "nextMessageId": nxt,
        "result": result,
    }


def run_engine(step: str, campaign_id: str, attempt: int = 1) -> dict[str, Any]:
    campaign = ledger.get_campaign(campaign_id) or {}
    campaign["id"] = campaign_id
    campaign["_harvestAttempt"] = attempt
    return dispatch(step, campaign)


def _maybe_start_harvest(campaign_id: str, pipeline: list[str], result: dict[str, Any]) -> None:
    assets = result.get("assets") or {}
    clip = assets.get("clip") or {}
    proof = assets.get("clipProof") or {}
    jingle = assets.get("jingle") or {}
    need = (
        bool(clip.get("operation"))
        or bool(proof.get("operation"))
        or bool(jingle.get("pending"))
    )
    if not need:
        return
    publish_step(
        campaign_id=campaign_id,
        step="inka_harvest",
        pipeline=pipeline,
        attempt=1,
    )


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


def _after_step(campaign_id: str, step: str, result: dict[str, Any]) -> None:
    try:
        from app.cost import estimate_campaign

        receipts = ledger.list_receipts(campaign_id)
        campaign = ledger.get_campaign(campaign_id)
        rec_list = receipts if isinstance(receipts, list) else []
        camp = campaign if isinstance(campaign, dict) else {}
        est = estimate_campaign(campaign_id, rec_list, campaign=camp)
        ledger.upsert_campaign(
            campaign_id,
            {
                "costUsd": est["estimatedUsd"],
                "costInr": est["estimatedInr"],
                "quotedInr": est["quotedInr"],
            },
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.notify import after_step

        campaign = ledger.get_campaign(campaign_id)
        if isinstance(campaign, dict):
            after_step(
                campaign_id,
                step,
                result if isinstance(result, dict) else {},
                campaign=campaign,
            )
    except Exception:  # noqa: BLE001
        pass

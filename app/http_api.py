# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""HTTP surface for Mission Control, judges, and Pub/Sub push."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from app.armor import ArmorBlocked
from app.campaigns import (
    approve_campaign,
    campaign_view,
    create_campaign,
    decode_pubsub_push,
    screen_text,
)
from app.settings import load_settings
from app.worker import handle_step


def attach_flock_routes(app: FastAPI) -> None:
    @app.get("/v1/infra")
    def infra() -> dict:
        s = load_settings()
        return {
            "project": s.project_id,
            "region": s.region,
            "firestore": s.firestore_database,
            "topics": {
                "campaignSteps": s.campaign_topic_path,
                "dlq": f"projects/{s.project_id}/topics/{s.dlq_topic}",
                "alerts": f"projects/{s.project_id}/topics/{s.alerts_topic}",
            },
            "buckets": {"media": s.media_bucket, "logs": s.logs_bucket},
            "modelArmor": f"projects/{s.project_id}/locations/{s.armor_location}/templates/{s.armor_template}",
            "memoryBankId": s.memory_bank_id or None,
        }

    @app.post("/v1/screen")
    def screen(body: dict) -> dict:
        text = (body or {}).get("text") or ""
        if not text:
            raise HTTPException(400, "text required")
        return screen_text(text)

    @app.post("/v1/campaigns")
    def create(body: dict) -> dict:
        brief = (body or {}).get("brief") or body or {}
        raw = (body or {}).get("rawText") or brief.get("rawText") or ""
        try:
            return create_campaign(brief, raw_text=raw)
        except ArmorBlocked as exc:
            raise HTTPException(status_code=403, detail={"error": "blocked", "verdict": exc.verdict}) from exc

    @app.get("/v1/campaigns/{campaign_id}")
    def get_one(campaign_id: str) -> dict:
        view = campaign_view(campaign_id)
        if not view:
            raise HTTPException(404, "campaign not found")
        return view

    @app.post("/v1/campaigns/{campaign_id}/approve")
    def approve(campaign_id: str) -> dict:
        try:
            return approve_campaign(campaign_id)
        except KeyError:
            raise HTTPException(404, "campaign not found") from None

    @app.post("/internal/pubsub/campaign-steps")
    async def pubsub_push(request: Request) -> dict:
        # Same image as flock-api; only the worker service consumes the topic.
        if load_settings().service_name not in {"flock-worker", "local"}:
            raise HTTPException(404, "not a worker")
        body = await request.json()
        try:
            message = decode_pubsub_push(body)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(400, f"bad pubsub envelope: {exc}") from exc
        try:
            return handle_step(message)
        except Exception as exc:  # noqa: BLE001 — nack by returning 500 so Pub/Sub retries
            raise HTTPException(500, f"step failed: {exc}") from exc

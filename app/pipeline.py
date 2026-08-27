# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Pub/Sub campaign-steps publisher. At-least-once; idempotency lives on the receipt."""

from __future__ import annotations

import json

from google.cloud import pubsub_v1

from app.settings import load_settings

_publisher: pubsub_v1.PublisherClient | None = None


def publisher() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def publish_step(
    *,
    campaign_id: str,
    step: str,
    pipeline: list[str],
    attempt: int = 1,
) -> str:
    settings = load_settings()
    if not settings.project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")
    topic = settings.campaign_topic_path
    body = {
        "campaignId": campaign_id,
        "step": step,
        "pipeline": pipeline,
        "attempt": attempt,
        "idempotencyKey": f"{campaign_id}:{step}:{attempt}",
    }
    future = publisher().publish(
        topic,
        json.dumps(body).encode("utf-8"),
        campaignId=campaign_id,
        step=step,
        attempt=str(attempt),
    )
    return future.result(timeout=30)


def publish_next(campaign_id: str, current: str, pipeline: list[str]) -> str | None:
    try:
        idx = pipeline.index(current)
    except ValueError:
        return None
    if idx + 1 >= len(pipeline):
        return None
    return publish_step(
        campaign_id=campaign_id,
        step=pipeline[idx + 1],
        pipeline=pipeline,
        attempt=1,
    )

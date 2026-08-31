# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public lock — blog visitors get the seeded kit, not hire / ADK / Vertex."""

from __future__ import annotations

import os

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.seed import DEMO_SHOP

SEED_ID = DEMO_SHOP["campaignId"]

_OFF = frozenset({"0", "false", "off", "no", "disabled"})

_STORY_GET = frozenset(
    {
        "/health",
        "/healthz",
        "/demo",
        "/dash",
        "/v1/dash",
        "/console",
        "/architecture",
        "/architecture.png",
        "/blog",
        "/blog.md",
        "/ops",
        f"/k/{SEED_ID}",
        f"/l/{SEED_ID}",
        f"/media/{SEED_ID}/still",
        f"/media/{SEED_ID}/ready",
    }
)

_INTERNAL_POST = frozenset({"/internal/pubsub/campaign-steps"})

_ASSETS_PREFIX = "/assets/flock/"
_SEED_MEDIA_PREFIX = f"/media/{SEED_ID}/"


def enabled() -> bool:
    return os.getenv("FLOCK_PUBLIC_LOCK", "1").strip().lower() not in _OFF


def is_seed_id(campaign_id: str) -> bool:
    return campaign_id == SEED_ID


def normalize_path(path: str) -> str:
    raw = (path or "/").split("?", 1)[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw != "/" and raw.endswith("/"):
        raw = raw.rstrip("/")
    return raw or "/"


def decide(method: str, path: str) -> str:
    """Return allow, redirect, or deny."""
    if not enabled():
        return "allow"
    verb = (method or "GET").upper()
    route = normalize_path(path)
    if verb in {"GET", "HEAD"} and route == "/":
        return "redirect"
    if verb in {"GET", "HEAD"}:
        if route in _STORY_GET:
            return "allow"
        if route.startswith(_ASSETS_PREFIX):
            name = route[len(_ASSETS_PREFIX) :]
            if name and "/" not in name and ".." not in name:
                return "allow"
            return "deny"
        if route.startswith(_SEED_MEDIA_PREFIX):
            return "allow"
        return "deny"
    if verb == "POST" and route in _INTERNAL_POST:
        return "allow"
    return "deny"


def deny_response() -> JSONResponse:
    return JSONResponse({"error": "not published"}, status_code=404)


async def public_lock(request: Request, call_next):
    choice = decide(request.method, request.url.path)
    if choice == "redirect":
        return RedirectResponse("/demo", status_code=303)
    if choice == "deny":
        return deny_response()
    return await call_next(request)


def install(app) -> None:
    if getattr(app.state, "flock_public_lock", False):
        return
    app.state.flock_public_lock = True
    app.middleware("http")(public_lock)

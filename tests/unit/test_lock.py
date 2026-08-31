# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.lock import decide, is_seed_id, normalize_path
from app.seed import DEMO_SHOP


def test_seed_id_is_exact() -> None:
    assert is_seed_id(DEMO_SHOP["campaignId"])
    assert not is_seed_id("google-listing-eaf57cae-evil")
    assert not is_seed_id("google-listing-eaf57cae/")
    assert not is_seed_id("")


def test_home_redirects() -> None:
    assert decide("GET", "/") == "redirect"
    assert decide("HEAD", "/") == "redirect"
    assert decide("GET", "/?") == "redirect"


def test_seeded_surface_is_public() -> None:
    cid = DEMO_SHOP["campaignId"]
    for path in (
        "/demo",
        f"/k/{cid}",
        f"/l/{cid}",
        f"/media/{cid}/still",
        f"/media/{cid}/ready",
        f"/media/{cid}/clip-feed",
        "/assets/flock/theater.js",
        "/blog",
        "/blog.md",
        "/dash",
        "/v1/dash",
        "/trace",
        "/v1/trace",
        "/architecture",
        "/health",
        "/healthz",
        "/ops",
    ):
        assert decide("GET", path) == "allow", path
        assert decide("HEAD", path) == "allow", path


def test_hire_and_adk_are_denied() -> None:
    cid = DEMO_SHOP["campaignId"]
    for method, path in (
        ("POST", "/"),
        ("POST", "/v1/campaigns"),
        ("GET", "/v1/campaigns"),
        ("GET", f"/v1/campaigns/{cid}"),
        ("POST", f"/v1/campaigns/{cid}/approve"),
        ("POST", "/v1/consents"),
        ("POST", "/v1/screen"),
        ("POST", "/v1/telegram/webhook"),
        ("GET", "/v1/infra"),
        ("GET", f"/r/{cid}"),
        ("GET", f"/s/{cid}"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("POST", "/run_sse"),
        ("POST", "/run"),
        ("GET", "/apps"),
        ("POST", "/apps/app/users/u/sessions"),
        ("GET", "/a2a/app/.well-known/agent-card.json"),
        ("GET", f"/k/{cid}-evil"),
        ("GET", f"/media/{cid}-evil/still"),
        ("GET", "/k/noya-salon-a1b2c3d4"),
        ("GET", "/assets/flock/../http_api.py"),
    ):
        assert decide(method, path) == "deny", f"{method} {path}"


def test_worker_push_is_allowed() -> None:
    assert decide("POST", "/internal/pubsub/campaign-steps") == "allow"
    assert decide("GET", "/internal/pubsub/campaign-steps") == "deny"


def test_normalize_strips_trailing_slash() -> None:
    assert normalize_path("/demo/") == "/demo"
    assert normalize_path("/") == "/"
    assert normalize_path("/k/google-listing-eaf57cae/") == "/k/google-listing-eaf57cae"

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.cost import estimate_campaign, owner_cost_blurb, usage_from_response
from app.telegram_adapter import allowlist, handle_update, verify_webhook_secret
from app.studio import check_key, render_html as render_studio
from app.demo import DEMO_SHOP, render_html as render_demo
from app.ops import extract_token, verify_token


def test_webhook_secret_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    assert verify_webhook_secret(None) is True
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    assert verify_webhook_secret("s3cret") is True
    assert verify_webhook_secret("nope") is False


def test_allowlist_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_ALLOW_USER_IDS", "11, 22")
    assert allowlist() == {"11", "22"}


@pytest.mark.asyncio
async def test_telegram_groups_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr("app.telegram_adapter.send_message", lambda _c, t: sent.append(t))
    out = await handle_update(
        {
            "message": {
                "text": "Glen's Bakehouse Indiranagar",
                "chat": {"id": 1, "type": "group"},
                "from": {"id": 9},
            }
        }
    )
    assert out.get("ignored") == "group"
    assert sent and "private" in sent[0].lower()


@pytest.mark.asyncio
async def test_telegram_allowlist_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setenv("TELEGRAM_ALLOW_USER_IDS", "99")
    monkeypatch.setattr("app.telegram_adapter.send_message", lambda _c, t: sent.append(t))
    out = await handle_update(
        {
            "message": {
                "text": "hello",
                "chat": {"id": 1, "type": "private"},
                "from": {"id": 9},
            }
        }
    )
    assert out.get("denied") is True


@pytest.mark.asyncio
async def test_telegram_start_is_flo_voiced(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.delenv("TELEGRAM_ALLOW_USER_IDS", raising=False)
    monkeypatch.setattr("app.telegram_adapter.send_message", lambda _c, t: sent.append(t))
    out = await handle_update(
        {
            "message": {
                "text": "/start",
                "chat": {"id": 7, "type": "private"},
                "from": {"id": 7},
            }
        }
    )
    assert out.get("greeted") is True
    assert "Flo" in sent[0]
    assert "autopost" in sent[0].lower()


def test_two_films_dominate_cogs() -> None:
    receipts = [
        {
            "step": "inka_harvest",
            "payload": {
                "clip": {
                    "gcs": "gs://bucket/clip.mp4",
                    "voices": {"en": {"ok": True}, "indic": {"ok": True}},
                },
                "clipProof": {
                    "gcs": "gs://bucket/proof.mp4",
                    "voices": {"en": {"ok": True}, "indic": {"ok": True}},
                },
            },
        }
    ]
    with patch("app.cost.ledger.get_campaign", return_value={"engineConfig": {"price_inr": 5997}}):
        est = estimate_campaign("c1", receipts)
    assert est["quotedInr"] == 5997
    assert est["estimatedUsd"] >= 6.4
    veo = [x for x in est["lines"] if x.get("kind") == "veo"]
    assert len(veo) == 2
    blurb = owner_cost_blurb(est)
    assert blurb["quotedInr"] == 5997
    assert "invoice" in blurb["note"].lower() or "Vertex" in blurb["note"]


def test_usage_from_response_reads_metadata() -> None:
    resp = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=1000,
            candidates_token_count=200,
            total_token_count=1200,
        )
    )
    row = usage_from_response(resp, model="gemini-3.5-flash", kind="text")
    assert row["inputTokens"] == 1000
    assert row["outputTokens"] == 200
    assert row["usd"] > 0


def test_public_trace_is_seed_burn_not_a_quote() -> None:
    receipts = [
        {
            "step": "scout",
            "status": "ok",
            "payload": {
                "groundingUris": ["https://example.test"],
                "usage": [
                    {
                        "model": "gemini-3.5-flash",
                        "kind": "text",
                        "inputTokens": 1000,
                        "outputTokens": 200,
                        "usd": 0.003,
                    }
                ],
            },
        },
        {
            "step": "inka_harvest",
            "status": "ok",
            "payload": {
                "clip": {"gcs": "gs://b/c.mp4", "voices": {"en": {"ok": True}, "indic": {"ok": True}}},
            },
        },
        {"step": "ad_kit", "status": "ok"},
    ]
    from app.cost import public_trace

    trace = public_trace("google-listing-eaf57cae", receipts, {})
    assert "quotedInr" not in trace
    assert trace["tokens"]["input"] == 1000
    assert trace["calls"] >= 2
    assert trace["estimatedUsd"] >= 3.2
    assert any(t["id"] == "google_search" for t in trace["tools"])
    assert any(t["id"] == "veo" for t in trace["tools"])
    assert "invoice" in trace["note"].lower()


def test_studio_key_is_compared() -> None:
    assert check_key({"studioKey": "abc"}, "abc") is True
    assert check_key({"studioKey": "abc"}, "xyz") is False
    assert check_key({}, "abc") is False


def test_studio_html_is_delivery_room_not_autopost() -> None:
    campaign = {
        "status": "completed",
        "brief": {"businessName": "Glen's Bakehouse", "geo": "Indiranagar"},
        "studioKey": "k",
        "landingPath": "/l/google-listing-eaf57cae",
        "kitPath": "/k/google-listing-eaf57cae",
    }
    receipts = [
        {
            "step": "inka",
            "payload": {
                "copy": {"headline": "Your quiet courtyard escape", "primaryText": "Mini red velvet cupcakes."},
                "brandSpec": {"themeId": "paper"},
                "locale": {"bcp47": "kn-IN", "nativeName": "ಕನ್ನಡ"},
            },
        },
        {
            "step": "ad_kit",
            "payload": {
                "variants": [
                    {
                        "id": "meta_feed",
                        "platform": "meta",
                        "aspect": "4:5",
                        "headline": "Your quiet courtyard escape",
                        "primaryText": "Mini red velvet cupcakes.",
                        "utmUrl": "https://example.test/l/google-listing-eaf57cae?utm_source=meta&utm_content=meta_feed",
                        "still": "/media/google-listing-eaf57cae/still-feed",
                        "clip": "/media/google-listing-eaf57cae/clip-feed",
                        "clipSlot": "clip-feed",
                        "width": 1080,
                        "height": 1350,
                    }
                ]
            },
        },
    ]
    hits = [{"kind": "landing_hit", "detail": {"utm_content": "meta_feed", "utm_source": "meta"}}]
    with (
        patch("app.studio.ledger.list_receipts", return_value=receipts),
        patch("app.studio.ledger.list_events", return_value=hits),
        patch("app.studio.media.campaign_asset_exists", return_value=True),
        patch("app.cost.ledger.get_campaign", return_value={"engineConfig": {"price_inr": 5997}}),
        patch("app.cost.ledger.list_receipts", return_value=receipts),
    ):
        html = render_studio("google-listing-eaf57cae", campaign)
    assert "delivery room" in html
    assert "We do not autopost" in html
    assert "₹" not in html
    assert "5997" not in html
    assert "utm_content" in html
    assert "meta_feed" in html
    assert "1080×1350" in html


def test_demo_page_is_seeded_bakehouse_kit() -> None:
    html = render_demo()
    assert DEMO_SHOP["name"] in html
    assert DEMO_SHOP["campaignId"] in html
    assert DEMO_SHOP["kitPath"] in html
    assert DEMO_SHOP["url"] in html
    assert "do not contact the bakery" in html.lower()
    assert "autopost" in html.lower()
    assert "Mira" not in html
    assert "Telegram is the meeting" not in html
    assert "Open Telegram" not in html
    assert "/?" in html


def test_ops_token_extract_and_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "ops-secret")
    assert verify_token("ops-secret") is True
    assert verify_token("nope") is False
    assert extract_token("h", None, None) == "h"
    assert extract_token(None, "Bearer abc", None) == "abc"
    assert extract_token(None, None, "q") == "q"

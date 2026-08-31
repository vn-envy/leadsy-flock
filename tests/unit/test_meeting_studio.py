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
                "text": "Mira's Chai Koramangala",
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


def test_studio_key_is_compared() -> None:
    assert check_key({"studioKey": "abc"}, "abc") is True
    assert check_key({"studioKey": "abc"}, "xyz") is False
    assert check_key({}, "abc") is False


def test_studio_html_is_delivery_room_not_autopost() -> None:
    campaign = {
        "status": "completed",
        "brief": {"businessName": "Mira's Chai", "geo": "Bangalore"},
        "studioKey": "k",
        "landingPath": "/l/mira-1",
        "kitPath": "/k/mira-1",
    }
    receipts = [
        {
            "step": "inka",
            "payload": {
                "copy": {"headline": "Evening cups", "primaryText": "Walk-past takeaway."},
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
                        "headline": "Evening cups",
                        "primaryText": "Walk-past takeaway.",
                        "utmUrl": "https://example.test/l/mira-1?utm_source=meta&utm_content=meta_feed",
                        "still": "/media/mira-1/still-feed",
                        "clip": "/media/mira-1/clip-feed",
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
        html = render_studio("mira-1", campaign)
    assert "delivery room" in html
    assert "We do not autopost" in html
    assert "₹5997" in html or "5997" in html
    assert "utm_content" in html
    assert "meta_feed" in html
    assert "1080×1350" in html


def test_demo_page_is_fictional_and_clocked() -> None:
    html = render_demo()
    assert DEMO_SHOP["name"] in html
    assert "YES" in html
    assert "autopost" in html.lower()
    assert "Glen" not in html
    assert "Telegram is the meeting" not in html
    assert "Open Telegram" not in html
    assert "/?" in html
    assert "name=" in html


def test_ops_token_extract_and_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "ops-secret")
    assert verify_token("ops-secret") is True
    assert verify_token("nope") is False
    assert extract_token("h", None, None) == "h"
    assert extract_token(None, "Bearer abc", None) == "abc"
    assert extract_token(None, None, "q") == "q"

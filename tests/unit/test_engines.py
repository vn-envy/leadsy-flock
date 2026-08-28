# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

import time
from unittest.mock import patch

from app.engines.gate import banned_hits, run as gate_run
from app.engines.adkit import variant, CHANNELS
from app.engines.stella import render_html
from app.engines import harvest, inka, outreach, scout


def test_banned_hits_catches_guaranteed() -> None:
    assert "guaranteed_outcome" in banned_hits("Guaranteed six-pack in 30 days")
    assert banned_hits("Evening sessions near Golf Course Road") == []


def test_ad_kit_variant_clips_and_utms() -> None:
    ch = CHANNELS[0]
    out = variant(
        ch,
        {
            "headline": "A very long headline that should be clipped for Meta feed limits because it ramble",
            "primaryText": "Short primary.",
            "cta": "See slots",
        },
        "https://example.test/l/c1",
        "c1",
    )
    assert out["lint"]["ok"] is True
    assert "utm_campaign=c1" in out["utmUrl"]
    assert out["charCounts"]["headline"] <= ch["headlineMax"]


def test_stella_html_requires_consent_checkbox() -> None:
    html = render_html(
        {"id": "peak-1", "brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}},
        {"headline": "Evenings that fit the commute", "cta": "I'm in"},
        {"palette": ["#c4a574", "#0f1419", "#f4efe6"]},
    )
    assert "consent first" in html
    assert 'name="consent" required' in html
    assert "/v1/consents" in html
    assert "Peak Gym" in html
    assert "<script" in html


def test_stella_html_embeds_still_when_present() -> None:
    html = render_html(
        {"id": "peak-1", "brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}},
        {"headline": "Evenings that fit the commute", "cta": "I'm in"},
        {"palette": ["#c4a574", "#0f1419", "#f4efe6"]},
        still_src="/media/peak-1/still",
    )
    assert 'src="/media/peak-1/still"' in html
    assert 'class="hero"' in html


def test_stella_html_embeds_clip_and_jingle_hooks() -> None:
    html = render_html(
        {"id": "peak-1", "brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}},
        {"headline": "Evenings that fit the commute", "cta": "I'm in"},
        {"palette": ["#c4a574", "#0f1419", "#f4efe6"]},
        still_src="/media/peak-1/still",
        clip_src="/media/peak-1/clip",
        jingle_src="/media/peak-1/jingle",
    )
    assert 'id="clip"' in html
    assert 'src="/media/peak-1/clip"' in html
    assert 'src="/media/peak-1/jingle"' in html
    assert "revealWhenReady" in html
    assert "/media/peak-1/ready" in html


def test_inka_run_never_raises() -> None:
    with patch.object(inka, "_run_inner", side_effect=RuntimeError("no vertex")):
        out = inka.run({"brief": {"businessName": "Peak Gym"}})
    assert "Guaranteed" in (out["copy"]["draftHeadline"] or "")
    assert "Peak Gym" in out["copy"]["headline"]
    assert out["errors"]


def test_scout_run_never_raises() -> None:
    with patch.object(scout, "_run_inner", side_effect=RuntimeError("no vertex")):
        out = scout.run({"brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}})
    assert out["brandSpec"]["tagline"]
    assert out["errors"]


def test_gemini_clients_are_cached() -> None:
    from app.engines import gemini_util as g

    g.text_client.cache_clear()
    g.media_client.cache_clear()
    g.image_client.cache_clear()
    assert g.text_client() is g.text_client()
    assert g.media_client() is g.media_client()
    assert g.image_client() is g.image_client()


def test_call_timeout_none_fallback() -> None:
    def slow() -> str:
        time.sleep(1)
        return "nope"

    assert inka._call_timeout(slow, 0.05, None) is None


def test_outreach_refuses_without_consent() -> None:
    with patch("app.engines.outreach.ledger.list_consents", return_value=[]):
        out = outreach.run_gate({"id": "c1"})
    assert out["verdict"] == "refuse"


def test_gate_rejects_draft_passes_clean_headline() -> None:
    payload = {
        "copy": {
            "draftHeadline": "Guaranteed six-pack in 30 days",
            "headline": "Evening sessions near Golf Course Road",
            "primaryText": "Book a slot that fits the commute.",
        }
    }
    with (
        patch("app.engines.gate.ledger.get_receipt", return_value={"payload": payload}),
        patch("app.engines.gate.ledger.write_memory"),
        patch("app.engines.gate._gemma_classify", return_value={"ok": True, "risk": "low", "labels": []}),
        patch("app.engines.gate._gemini_judge", return_value={"ok": True, "verdict": "pass"}),
    ):
        out = gate_run({"id": "c1"})
    assert out["draft"]["rejected"] is True
    assert out["verdict"] == "pass"


def test_harvest_retries_while_veo_is_running(monkeypatch) -> None:
    monkeypatch.setenv("INKA_SKIP_LYRIA", "1")
    with (
        patch("app.engines.harvest.ledger.get_receipt", return_value={
            "payload": {
                "assets": {"clip": {"operation": "ops/abc", "status": "started"}},
                "prompts": {},
            }
        }),
        patch("app.engines.harvest.ledger.upsert_campaign"),
        patch("app.engines.harvest.media.campaign_asset_exists", return_value=False),
        patch.object(harvest, "_poll_veo", return_value={"operation": "ops/abc", "status": "started", "ok": True}),
    ):
        out = harvest.run({"id": "c1", "_harvestAttempt": 1})
    assert out["retry"] is True


def test_harvest_finishes_when_clip_has_gcs(monkeypatch) -> None:
    monkeypatch.setenv("INKA_SKIP_LYRIA", "1")
    harvested = {
        "operation": "ops/abc",
        "status": "harvested",
        "ok": True,
        "gcs": "gs://bucket/clip.mp4",
        "bytes": 12,
        "publicPath": "/media/c1/clip",
    }
    with (
        patch("app.engines.harvest.ledger.get_receipt", return_value={
            "payload": {
                "assets": {"clip": {"operation": "ops/abc", "status": "started"}},
                "prompts": {},
            }
        }),
        patch("app.engines.harvest.ledger.upsert_campaign") as upsert,
        patch("app.engines.harvest.media.campaign_asset_exists", return_value=False),
        patch.object(harvest, "_poll_veo", return_value=harvested),
    ):
        out = harvest.run({"id": "c1", "_harvestAttempt": 2})
    assert out["retry"] is False
    assert out["clip"]["gcs"]
    upsert.assert_called_once()


def test_harvest_skips_lyria_after_retries(monkeypatch) -> None:
    monkeypatch.setenv("INKA_SKIP_LYRIA", "0")
    with (
        patch("app.engines.harvest.ledger.get_receipt", return_value={
            "payload": {
                "assets": {
                    "clip": {"ok": True, "status": "harvested", "gcs": "gs://b/c.mp4"},
                    "jingle": {"pending": True},
                },
                "prompts": {"lyria": "sting"},
            }
        }),
        patch("app.engines.harvest.ledger.upsert_campaign"),
        patch.object(harvest, "_lyria") as lyria,
    ):
        out = harvest.run({"id": "c1", "_harvestAttempt": 3})
    lyria.assert_not_called()
    assert out["jingle"]["skipped"] is True
    assert out["jingle"]["pending"] is False
    assert out["retry"] is False

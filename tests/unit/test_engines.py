# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

import time
from unittest.mock import patch

from app.engines.gate import banned_hits, run as gate_run
from app.engines.adkit import variant, CHANNELS, render_kit, run as adkit_run
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
    assert out["aspect"] == "4:5"
    assert out["still"] == "/media/c1/still-feed"
    assert out["clip"] == "/media/c1/clip-feed"


def test_ad_kit_html_is_paste_guide_not_autopost() -> None:
    inka_payload = {
        "copy": {
            "headline": "Colour that fits the commute",
            "subhead": "Evenings on Golf Course Road.",
            "primaryText": "Book a colour slot after work.",
            "cta": "See slots",
            "storyHook": "Quiet colour after work, not an influencer set.",
            "voIndic": "ऑफिस के बाद, कैमरा नहीं — सिर्फ रंग।",
            "voEn": "Evenings that fit the commute. Just the work.",
            "headlineLocalized": "ऑफिस के बाद वाला रंग",
            "primaryTextLocalized": "डीएलएफ के पास शांत रंग।",
        },
        "brandSpec": {"themeId": "paper"},
        "locale": {"bcp47": "hi-IN", "script": "Devanagari", "nativeName": "हिन्दी", "code": "hi"},
        "shelf": [
            {
                "uri": "https://www.facebook.com/ads/library/?id=example",
                "title": "Quiet salon craft",
                "hookType": "anti-influencer",
            }
        ],
        "assets": {},
    }
    stella_payload = {"url": "https://example.test/l/noya-1", "landing": "/l/noya-1"}

    def receipts(_cid: str, step: str):
        if step == "inka":
            return {"payload": inka_payload}
        if step == "stella":
            return {"payload": stella_payload}
        return {}

    with (
        patch("app.engines.adkit.ledger.get_receipt", side_effect=receipts),
        patch("app.engines.adkit.ledger.upsert_campaign") as upsert,
    ):
        out = adkit_run(
            {"id": "noya-1", "brief": {"businessName": "Noya Salon", "geo": "Gurgaon"}}
        )
    assert out["autopost"] is False
    assert out["kit"] == "/k/noya-1"
    assert out["themeId"] == "paper"
    html = upsert.call_args.args[1]["kitHtml"]
    assert upsert.call_args.args[1]["kitPath"] == "/k/noya-1"
    assert 'data-theme="paper"' in html
    assert "--bg:#f7f1e8" in html
    assert "We do not autopost" in html
    assert "/media/noya-1/still-feed" in html
    assert "/media/noya-1/clip-captioned" in html
    assert "/media/noya-1/clip-en" in html
    assert "/media/noya-1/clip-indic" in html
    assert "VO English" in html
    assert "this shop's own photos" in html
    assert "anti-influencer" in html
    assert "hi-IN" in html
    assert "ऑफिस" in html
    assert "/media/noya-1/still-landscape" in html
    assert "whatsapp_status" in html
    assert "google_rsa" in html
    assert "/media/noya-1/ready" in html
    assert "video.thumb[hidden]" in html
    assert render_kit(
        {"id": "noya-1", "brief": {"businessName": "Noya Salon", "geo": "Gurgaon"}},
        inka_payload["copy"],
        inka_payload["brandSpec"],
        out["variants"],
        "/l/noya-1",
    ).count("<article") == 6


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
    assert "--bg:" in html
    assert "var(--fg)" in html


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
    assert out["brandSpec"]["themeId"] == "ember"
    assert out["locale"]["bcp47"] == "hi-IN"
    assert out["shelf"] == []
    assert out["errors"]


def test_scout_salon_fallback_is_paper() -> None:
    with patch.object(scout, "_run_inner", side_effect=RuntimeError("no vertex")):
        out = scout.run({"brief": {"businessName": "Noya Salon", "geo": "Gurgaon"}})
    assert out["brandSpec"]["themeId"] == "paper"


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
        patch.object(harvest, "derive_videos", return_value={"ok": True, "slots": {}}),
        patch.object(harvest, "burn_story_captions", return_value={"ok": True}),
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
        patch.object(harvest, "derive_videos", return_value={"ok": True, "slots": {"story": {"ok": True}}}),
        patch.object(harvest, "burn_story_captions", return_value={"ok": True, "publicPath": "/media/c1/clip-captioned"}),
        patch.object(harvest, "dual_tracks", return_value={"en": {"ok": True}}),
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
        patch.object(harvest, "derive_videos", return_value={"ok": True, "slots": {}}),
        patch.object(harvest, "burn_story_captions", return_value={"ok": True}),
        patch.object(harvest, "dual_tracks", return_value={"en": {"ok": True}}),
    ):
        out = harvest.run({"id": "c1", "_harvestAttempt": 3})
    lyria.assert_not_called()
    assert out["jingle"]["skipped"] is True
    assert out["jingle"]["pending"] is False
    assert out["retry"] is False


def test_harvest_restarts_veo_after_rai_filter(monkeypatch) -> None:
    monkeypatch.setenv("INKA_SKIP_LYRIA", "1")
    rai = {
        "operation": "ops/refs",
        "status": "done_no_bytes",
        "ok": False,
        "usedRefs": True,
        "aspectRatio": "9:16",
        "raiReasons": ["people/face generation filtered out 1 videos"],
    }
    started = {
        "ok": True,
        "status": "started",
        "operation": "ops/plain",
        "usedRefs": False,
        "aspectRatio": "9:16",
        "generateAudio": True,
        "durationSeconds": 8,
    }
    with (
        patch("app.engines.harvest.ledger.get_receipt", return_value={
            "payload": {
                "assets": {"clip": {"operation": "ops/refs", "status": "started", "usedRefs": True}},
                "prompts": {"veo": "empty salon"},
                "copy": {"voEn": "Quiet colour after work."},
            }
        }),
        patch("app.engines.harvest.ledger.upsert_campaign"),
        patch("app.engines.harvest.media.campaign_asset_exists", return_value=False),
        patch.object(harvest, "_poll_veo", return_value=rai),
        patch.object(harvest, "_veo_start", return_value=started) as start,
        patch.object(harvest, "derive_videos", return_value={"ok": True, "slots": {}}),
        patch.object(harvest, "burn_story_captions", return_value={"ok": True}),
    ):
        out = harvest.run({"id": "c1", "_harvestAttempt": 3})
    start.assert_called_once()
    assert start.call_args.kwargs["sequence"] == ((False, "9:16"), (False, "16:9"))
    assert out["retry"] is True
    assert out["clip"]["operation"] == "ops/plain"
    assert out["clip"]["usedRefs"] is False
    assert out["clip"]["fallbackStage"] == 1

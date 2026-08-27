# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.engines.gate import banned_hits
from app.engines.adkit import variant, CHANNELS
from app.engines.stella import render_html


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

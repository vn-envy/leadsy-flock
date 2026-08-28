# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.captions import ass_document, _ass_escape, _wrap
from app.derive import video_encode_args
from app.engines.gate import banned_hits
from app.locale import resolve_locale, sanitize_shelf


def test_gurgaon_is_hindi() -> None:
    loc = resolve_locale("Gurgaon")
    assert loc["bcp47"] == "hi-IN"
    assert loc["script"] == "Devanagari"


def test_chennai_is_tamil() -> None:
    assert resolve_locale("Chennai, Tamil Nadu")["bcp47"] == "ta-IN"


def test_pune_is_marathi() -> None:
    assert resolve_locale("Pune")["bcp47"] == "mr-IN"


def test_sanitize_shelf_drops_invented_and_private() -> None:
    rows = sanitize_shelf(
        [
            {"uri": "not-a-url", "hookType": "craft"},
            {"uri": "https://www.facebook.com/people/Jane/123", "title": "person"},
            {
                "uri": "https://www.facebook.com/ads/library/?id=1",
                "title": "Meta library",
                "hookType": "anti-influencer",
                "snippet": "quiet salon vs ring light",
            },
        ]
    )
    assert len(rows) == 1
    assert rows[0]["hookType"] == "anti-influencer"
    assert rows[0]["uri"].startswith("https://")


def test_gate_catches_hindi_guarantee() -> None:
    assert "guaranteed_outcome" in banned_hits("इस महीने गारंटी परिणाम")


def test_video_encode_keeps_audio_by_default() -> None:
    args = video_encode_args()
    assert "-an" not in args
    assert "aac" in args
    assert "-an" in video_encode_args(audio=False)


def test_ass_wrap_and_escape() -> None:
    assert "\\N" in _wrap("one two three four five six seven eight nine ten", 12)
    assert "(" in _ass_escape("{bad}")
    doc = ass_document("ऑफिस के बाद शांत रंग", font="/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf")
    assert "Dialogue:" in doc
    assert "ऑफिस" in doc

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from pathlib import Path

from app.design import THEMES, assert_readable, contrast, resolve_theme
from app.engines.stella import render_html


def test_every_theme_meets_aa() -> None:
    for theme in THEMES.values():
        assert_readable(theme)
        assert contrast(theme.fg, theme.bg) >= 7


def test_peak_gym_orange_is_accent_not_canvas() -> None:
    theme = resolve_theme({"palette": ["#1A1A1A", "#FF6B00", "#FFFFFF"]})
    assert theme.id == "ember"
    assert theme.bg.lower() != "#ff6b00"
    assert theme.fg.lower() != "#ff6b00"
    html = render_html(
        {"id": "peak-1", "brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}},
        {"headline": "Evenings that fit the commute", "cta": "I'm in"},
        {"palette": ["#1A1A1A", "#FF6B00", "#FFFFFF"]},
    )
    assert "--bg:#16120f" in html
    assert "background: var(--bg)" in html
    assert 'data-theme="ember"' in html
    assert ".hero[hidden]" in html
    assert "#ff6b00" in html  # allowed as accent
    # The loud orange must not be the body fill via a raw assignment.
    assert "background:#FF6B00" not in html
    assert "background: #FF6B00" not in html


def test_named_theme_id_wins() -> None:
    theme = resolve_theme({"themeId": "paper", "palette": ["#FF6B00", "#000000", "#ffffff"]})
    assert theme.id == "paper"
    assert theme.bg == "#f7f1e8"


def test_design_md_lists_locked_tokens() -> None:
    text = Path(__file__).resolve().parents[2].joinpath("design.md").read_text(encoding="utf-8")
    for name, theme in THEMES.items():
        assert name in text
        assert theme.bg in text
        assert theme.fg in text
        assert theme.accent in text
    assert "4:5" in text
    assert "9:16" in text
    assert "1.91:1" in text
    assert "/k/{id}" in text
    assert "No autopost" in text

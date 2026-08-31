# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public shooting bible — readable page, not a raw .md."""

from __future__ import annotations

from pathlib import Path

from app.blog_ui import render_post

VIDEO = Path(__file__).resolve().parent / "video.md"


def render_html() -> str:
    return render_post(
        VIDEO,
        kicker="Shooting bible · 4 minutes",
        here="video",
        md_href="/video.md",
    )

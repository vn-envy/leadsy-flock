# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Seeded judge demo — Glen's Bakehouse kit already on the record. Do not contact the shop."""

from __future__ import annotations

from urllib.parse import urlencode

from app.run_ui import render_theater
from app.seed import DEMO_SHOP


def capture_prefill() -> str:
    return "/?" + urlencode(
        {
            "play": "seed",
            "url": DEMO_SHOP["url"],
            "name": DEMO_SHOP["name"],
            "geo": DEMO_SHOP["geo"],
            "goal": DEMO_SHOP["goal"],
        }
    )


def render_html() -> str:
    return render_theater(
        play="seed",
        url=DEMO_SHOP["url"],
        name=DEMO_SHOP["name"],
        geo=DEMO_SHOP["geo"],
        goal=DEMO_SHOP["goal"],
    )

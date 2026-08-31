# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Clocked judge demo — fictional shop, stopwatch on YES. Not a real business."""

from __future__ import annotations

from urllib.parse import urlencode

DEMO_SHOP = {
    "name": "Mira's Chai",
    "geo": "Koramangala, Bangalore",
    "goal": "Evening takeaway cups from office workers walking past the stall.",
    "brief": (
        "Mira's Chai, Koramangala Bangalore. Small stall, masala and ginger. "
        "Want evening takeaway cups from people walking home from offices. "
        "No website — I'll describe the stall: steel kettle, two clay cups, yellow awning."
    ),
}


def capture_prefill() -> str:
    return "/?" + urlencode(
        {
            "name": DEMO_SHOP["name"],
            "geo": DEMO_SHOP["geo"],
            "goal": DEMO_SHOP["goal"],
        }
    )


def render_html() -> str:
    name = DEMO_SHOP["name"]
    geo = DEMO_SHOP["geo"]
    brief = DEMO_SHOP["brief"]
    prefill = capture_prefill()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Judge clock · Leadsy Flock</title>
  <style>
    body {{ margin:0; background:#14181f; color:#f3eee6; font-family:system-ui,sans-serif; }}
    main {{ width:min(40rem, calc(100% - 2rem)); margin:0 auto; padding:2.5rem 0 4rem; }}
    h1 {{ font-family:Georgia,serif; font-weight:500; }}
    .kicker {{ letter-spacing:.2em; font-size:12px; color:#c4a574; font-weight:600; }}
    a {{ color:#c4a574; }}
    .copy {{ line-height:1.55; color:#b7aea2; }}
    ol {{ line-height:1.7; padding-left:1.2rem; }}
    .card {{
      background:#1c222c; border:1px solid #2c3340; border-radius:1rem;
      padding:1rem 1.1rem; margin:1.2rem 0;
    }}
    code, pre {{ font-size:.85rem; color:#f3eee6; white-space:pre-wrap; }}
    .pill {{
      display:inline-flex; background:#c4a574; color:#14181f; border-radius:999px;
      padding:.65rem 1.1rem; font-weight:650; text-decoration:none;
    }}
  </style>
</head>
<body>
<main>
  <p class="kicker">ALL THINGS AGENTIC · CLOCKED DEMO</p>
  <h1>Brief Flo. Time the kit.</h1>
  <p class="copy">Fictional stall — {name}, {geo}. Do not contact a real shop. We never autopost.
  The form is the meeting. The run URL is the delivery room.</p>
  <p><a class="pill" href="{prefill}">Open the prefilled form</a></p>
  <div class="card">
    <p class="kicker">Name, geo, goal are prefilled. You still paste a URL.</p>
    <pre>{brief}</pre>
  </div>
  <ol>
    <li>Open <a href="{prefill}">/</a> (name/geo/goal prefilled) and start the stopwatch.</li>
    <li>Paste a listing or website <strong>you own</strong> — Mira's stall has none. Any public shop URL works for the clock. Do not paste a business you do not operate.</li>
    <li>Get the quote (Scout + Inka + Stella). Tap <strong>YES</strong>. Stopwatch stays running — the run URL is the same the whole time.</li>
    <li>Watch Scout → Inka → Gate → Stella → Ad Kit. Studio iframe opens when the kit is ready.</li>
    <li>Open a UTM from the kit on the landing. Studio hit counter moves. That is “running ads” without autopost.</li>
    <li>Founder screen: token-gated <a href="/ops">/ops</a> — quoted vs burn.</li>
  </ol>
  <p class="copy">Films fill in on the same URL when Veo finishes (~minutes, not a Friday delivery).
  Do not use a live Google listing as the sales hero unless you own it.</p>
  <p class="copy"><a href="/">Capture</a> · <a href="/console">Mission Control</a> · <a href="/v1/infra">infra</a></p>
</main>
</body>
</html>
"""

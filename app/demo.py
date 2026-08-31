# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Seeded judge demo — Glen's Bakehouse kit already on the record. Do not contact the shop."""

from __future__ import annotations

from urllib.parse import urlencode

DEMO_SHOP = {
    "name": "Glen's Bakehouse",
    "geo": "Indiranagar, Bangalore",
    "goal": "Walk-ins to the courtyard for mini red velvet cupcakes.",
    "url": "https://share.google/rLF34cfolz9TJA92F",
    "website": "https://glensbakehouse.com/",
    "campaignId": "google-listing-eaf57cae",
    "kitPath": "/k/google-listing-eaf57cae",
    "landingPath": "/l/google-listing-eaf57cae",
    "utmPath": (
        "/l/google-listing-eaf57cae"
        "?utm_source=meta&utm_medium=paid"
        "&utm_campaign=google-listing-eaf57cae&utm_content=meta_feed"
    ),
    "stillPath": "/media/google-listing-eaf57cae/still-feed",
    "clipFeed": "/media/google-listing-eaf57cae/clip-feed",
    "clipProof": "/media/google-listing-eaf57cae/clip-proof-feed",
    "clipEn": "/media/google-listing-eaf57cae/clip-en",
    "clipIndic": "/media/google-listing-eaf57cae/clip-indic",
    "headline": "Your quiet courtyard escape in the heart of Indiranagar",
    "brief": (
        "Glen's Bakehouse, Indiranagar Bangalore. Public Google listing plus glensbakehouse.com. "
        "Own courtyard and cupcake photos. Hindi + English kit. We never autopost. "
        "Do not email, call, or review this bakery."
    ),
}


def capture_prefill() -> str:
    return "/?" + urlencode(
        {
            "url": DEMO_SHOP["url"],
            "name": DEMO_SHOP["name"],
            "geo": DEMO_SHOP["geo"],
            "goal": DEMO_SHOP["goal"],
        }
    )


def render_html() -> str:
    s = DEMO_SHOP
    prefill = capture_prefill()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Seeded kit · Glen's Bakehouse</title>
  <style>
    :root {{
      --bg:#14181f; --fg:#f3eee6; --muted:#b7aea2; --accent:#c4a574;
      --accent-fg:#14181f; --surface:#1c222c; --line:#2c3340;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--fg); font-family:system-ui,sans-serif; }}
    main {{ width:min(72rem, calc(100% - 2rem)); margin:0 auto; padding:2.5rem 0 4rem; }}
    h1 {{ font-family:Georgia,serif; font-weight:500; font-size:clamp(1.8rem,4vw,2.6rem); margin:0 0 .6rem; }}
    .kicker {{ letter-spacing:.2em; font-size:12px; color:var(--accent); font-weight:600; }}
    a {{ color:var(--accent); }}
    .copy {{ line-height:1.55; color:var(--muted); max-width:42rem; }}
    ol {{ line-height:1.7; padding-left:1.2rem; max-width:42rem; }}
    .card, .panel {{
      background:var(--surface); border:1px solid var(--line); border-radius:1rem;
      padding:1rem 1.1rem; margin:1.2rem 0;
    }}
    .pill {{
      display:inline-flex; background:var(--accent); color:var(--accent-fg); border-radius:999px;
      padding:.65rem 1.1rem; font-weight:650; text-decoration:none; margin:.2rem .4rem .2rem 0;
    }}
    .pill.ghost {{ background:transparent; color:var(--accent); border:1px solid var(--line); }}
    .grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr)); }}
    img.thumb, video.thumb {{
      width:100%; border-radius:.7rem; border:1px solid var(--line); background:var(--bg);
    }}
    iframe.kit {{
      width:100%; min-height:70vh; border:1px solid var(--line); border-radius:1rem; background:var(--bg);
    }}
    code, pre {{ font-size:.85rem; color:var(--fg); white-space:pre-wrap; }}
    .muted {{ color:var(--muted); font-size:.85rem; }}
  </style>
</head>
<body>
<main>
  <p class="kicker">ALL THINGS AGENTIC · SEEDED DEMO</p>
  <h1>{s["headline"]}</h1>
  <p class="copy">{s["name"]}, {s["geo"]}. This is the finished kit from a public Google listing —
  own bakery photos, 8s Veo, English + Hindi VO, every ad size. Do not contact the bakery.
  We never autopost.</p>
  <p>
    <a class="pill" href="{s["kitPath"]}">Open the paste kit</a>
    <a class="pill ghost" href="{s["utmPath"]}">Landing with a UTM</a>
    <a class="pill ghost" href="{prefill}">See the brief that produced it</a>
  </p>
  <div class="grid">
    <div>
      <p class="kicker">Place · 4:5</p>
      <img class="thumb" src="{s["stillPath"]}" alt="Glen's Bakehouse still"/>
      <video class="thumb" src="{s["clipFeed"]}" muted playsinline controls loop></video>
    </div>
    <div>
      <p class="kicker">Proof · 4:5</p>
      <video class="thumb" src="{s["clipProof"]}" muted playsinline controls loop></video>
      <p class="muted" style="margin:.6rem 0 0">English 9:16 <a href="{s["clipEn"]}">clip-en</a> ·
      Hindi 9:16 <a href="{s["clipIndic"]}">clip-indic</a></p>
    </div>
  </div>
  <div class="card">
    <p class="kicker">The brief on the record</p>
    <pre>{s["brief"]}
Listing: {s["url"]}
Site: {s["website"]}
Campaign: {s["campaignId"]}</pre>
  </div>
  <ol>
    <li>This page is the seeded demo. The kit is already complete — do not tap YES on a second run of this listing.</li>
    <li>Open the <a href="{s["kitPath"]}">paste kit</a>. Copy RSA lines and UTMs. Films are the shop's own frames, not an invented storefront.</li>
    <li>On a second device, open the <a href="{s["utmPath"]}">landing UTM</a>. Consent is still a checkbox. That is “running ads” without autopost.</li>
    <li>The capture form at <a href="{prefill}">/</a> is prefilled with this listing so you can see the door. Use a shop <strong>you own</strong> if you want a fresh YES.</li>
    <li>Founder screen: token-gated <a href="/ops">/ops</a> — quoted vs burn. Veo dominates COGS.</li>
  </ol>
  <p class="kicker">Full kit</p>
  <iframe class="kit" title="Glen's Bakehouse paste kit" src="{s["kitPath"]}" sandbox="allow-scripts allow-same-origin allow-popups"></iframe>
  <p class="copy" style="margin-top:1.5rem"><a href="/">Capture</a> · <a href="/console">Mission Control</a> · <a href="/v1/infra">infra</a></p>
</main>
</body>
</html>
"""

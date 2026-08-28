# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka-Adapt — one gated master → Meta / Google / WhatsApp kit. Never auto-posted."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote

from app import ledger
from app.design import resolve_theme


CHANNELS = (
    {
        "id": "meta_feed",
        "platform": "meta",
        "placement": "feed",
        "aspect": "4:5",
        "primaryMax": 125,
        "headlineMax": 40,
        "stillSlot": "still-feed",
        "clipSlot": "clip-feed",
    },
    {
        "id": "meta_square",
        "platform": "meta",
        "placement": "carousel",
        "aspect": "1:1",
        "primaryMax": 125,
        "headlineMax": 40,
        "stillSlot": "still-square",
        "clipSlot": "clip-square",
    },
    {
        "id": "meta_reel",
        "platform": "meta",
        "placement": "reel",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-story",
    },
    {
        "id": "whatsapp_status",
        "platform": "whatsapp",
        "placement": "status",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-story",
        "organic": True,
    },
    {
        "id": "google_display",
        "platform": "google",
        "placement": "display",
        "aspect": "1.91:1",
        "primaryMax": 90,
        "headlineMax": 30,
        "stillSlot": "still-landscape",
        "clipSlot": "clip-landscape",
    },
    {
        "id": "google_rsa",
        "platform": "google",
        "placement": "search",
        "aspect": "text",
        "headlineMax": 30,
        "descriptionMax": 90,
    },
)


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    stella = (ledger.get_receipt(campaign_id, "stella") or {}).get("payload") or {}
    copy = inka.get("copy") or {}
    brand = inka.get("brandSpec") or {}
    landing = stella.get("url") or stella.get("landing") or ""
    variants = [variant(ch, copy, landing, campaign_id) for ch in CHANNELS]
    page = render_kit(campaign, copy, brand, variants, landing)
    path = f"/k/{campaign_id}"
    ledger.upsert_campaign(campaign_id, {"kitHtml": page, "kitPath": path})
    return {
        "autopost": False,
        "note": "Ready to upload. Owner makes the final click on their own channels.",
        "landing": landing,
        "kit": path,
        "themeId": resolve_theme(brand).id,
        "variants": variants,
        "assets": inka.get("assets") or {},
    }


def variant(channel: dict[str, Any], copy: dict[str, Any], landing: str, campaign_id: str) -> dict[str, Any]:
    headline = _clip(str(copy.get("headline") or ""), int(channel.get("headlineMax") or 40))
    primary = _clip(str(copy.get("primaryText") or copy.get("subhead") or ""), int(channel.get("primaryMax") or 125))
    cta = str(copy.get("cta") or "Learn more")
    utm = _utm(landing, campaign_id, channel["id"])
    lint = _lint(channel, headline, primary)
    block: dict[str, Any] = {
        "id": channel["id"],
        "platform": channel["platform"],
        "placement": channel["placement"],
        "aspect": channel["aspect"],
        "headline": headline,
        "primaryText": primary,
        "cta": cta,
        "utmUrl": utm,
        "lint": lint,
        "organic": bool(channel.get("organic")),
        "charCounts": {
            "headline": len(headline),
            "primaryText": len(primary),
        },
    }
    if channel.get("stillSlot"):
        block["still"] = f"/media/{campaign_id}/{channel['stillSlot']}"
        block["stillSlot"] = channel["stillSlot"]
    if channel.get("clipSlot"):
        block["clip"] = f"/media/{campaign_id}/{channel['clipSlot']}"
        block["clipSlot"] = channel["clipSlot"]
    if channel["id"] == "google_rsa":
        desc = _clip(str(copy.get("subhead") or primary), int(channel.get("descriptionMax") or 90))
        block["description"] = desc
        block["charCounts"]["description"] = len(desc)
        block["headlines"] = [headline, _clip(cta, 30), _clip("Evenings near you", 30)]
    return block


def render_kit(
    campaign: dict[str, Any],
    copy: dict[str, Any],
    brand: dict[str, Any],
    variants: list[dict[str, Any]],
    landing: str,
) -> str:
    theme = resolve_theme(brand)
    brief = campaign.get("brief") or {}
    business = html.escape(str(brief.get("businessName") or "Campaign"))
    geo = html.escape(str(brief.get("geo") or ""))
    cid = html.escape(str(campaign.get("id") or ""))
    headline = html.escape(str(copy.get("headline") or ""))
    sub = html.escape(str(copy.get("subhead") or ""))
    cta = html.escape(str(copy.get("cta") or "Learn more"))
    land_href = html.escape(landing or f"/l/{cid}")
    cards = []
    for v in variants:
        vid = html.escape(str(v.get("id") or ""))
        aspect = html.escape(str(v.get("aspect") or ""))
        still = html.escape(str(v.get("still") or ""))
        clip = html.escape(str(v.get("clip") or ""))
        h = html.escape(str(v.get("headline") or ""))
        p = html.escape(str(v.get("primaryText") or ""))
        u = html.escape(str(v.get("utmUrl") or ""))
        kind = "organic" if v.get("organic") else v.get("platform")
        media_bits = ""
        if still:
            media_bits += f'<img class="thumb" src="{still}" alt="{vid} still" />'
        if clip:
            slot = html.escape(str(v.get("clipSlot") or clip.rsplit("/", 1)[-1]))
            media_bits += (
                f'<video class="thumb" data-slot="{slot}" src="{clip}" '
                f'muted playsinline controls loop hidden></video>'
            )
        rsa = ""
        if v.get("headlines"):
            lines = "".join(f"<li>{html.escape(str(x))}</li>" for x in v["headlines"])
            rsa = f"<p class='label'>RSA headlines</p><ul>{lines}</ul>"
            if v.get("description"):
                rsa += f"<p class='label'>Description</p><p class='copy'>{html.escape(str(v['description']))}</p>"
        cards.append(
            f"""<article class="card" data-id="{vid}">
  <p class="kicker">{html.escape(str(kind))} · {aspect}</p>
  <h2>{vid}</h2>
  <div class="thumbs">{media_bits or "<p class='muted'>Text only</p>"}</div>
  <p class="label">Headline</p><p class="copy">{h}</p>
  <p class="label">Primary</p><p class="copy">{p}</p>
  {rsa}
  <p class="label">UTM</p><p class="copy utm">{u}</p>
  <p class="muted">CTA: {html.escape(str(v.get("cta") or cta))}</p>
</article>"""
        )
    cards_html = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en" data-theme="{html.escape(theme.id)}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="color-scheme" content="{theme.scheme}"/>
  <title>Kit · {business}</title>
  <style>
    :root {{ {theme.css_vars()} }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; background: var(--bg); color: var(--fg);
      font-family: system-ui, "Segoe UI", sans-serif;
    }}
    main {{ width: min(72rem, calc(100% - 2rem)); margin: 0 auto; padding: 2.5rem 0 4rem; }}
    .kicker {{ letter-spacing: .16em; font-size: .75rem; text-transform: uppercase; color: var(--accent); font-weight: 650; margin: 0 0 .6rem; }}
    h1 {{ font-family: Georgia, serif; font-weight: 500; font-size: clamp(1.6rem, 4vw, 2.4rem); margin: 0 0 .4rem; }}
    .lede {{ color: var(--muted); max-width: 40rem; line-height: 1.55; }}
    a {{ color: var(--accent); }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); margin-top: 2rem; }}
    .card {{
      background: var(--surface); border: 1px solid var(--line);
      border-radius: 1rem; padding: 1rem 1rem 1.1rem;
    }}
    .card h2 {{ font-size: .95rem; margin: 0 0 .75rem; font-weight: 650; }}
    .thumbs {{ display: grid; gap: .5rem; margin-bottom: .85rem; }}
    .thumb {{
      width: 100%; max-height: 16rem; object-fit: cover;
      border-radius: .6rem; background: var(--bg); border: 1px solid var(--line);
    }}
    video.thumb[hidden] {{ display: none; }}
    .label {{ font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin: .7rem 0 .2rem; }}
    .copy {{ margin: 0; font-size: .92rem; line-height: 1.45; word-break: break-word; }}
    .utm {{ font-size: .78rem; color: var(--muted); }}
    .muted {{ color: var(--muted); font-size: .85rem; }}
    ul {{ margin: .2rem 0 .4rem 1.1rem; padding: 0; }}
    .note {{ margin-top: 2rem; color: var(--muted); font-size: .85rem; }}
  </style>
</head>
<body>
<main>
  <p class="kicker">{business} · {geo} · asset kit</p>
  <h1>{headline or "Launch kit"}</h1>
  <p class="lede">{sub} Copy stays off the pixels — upload the file, paste the text. We do not autopost.
  <a href="{land_href}">Consent landing</a>.</p>
  <div class="grid">
    {cards_html}
  </div>
  <p class="note">Ratios follow design.md: 4:5 feed, 1:1 carousel, 9:16 Reels/WhatsApp, 1.91:1 Google display, 16:9 on the landing. Veo clips appear here once harvest writes GCS.</p>
</main>
<script>
  async function revealClips() {{
    const videos = [...document.querySelectorAll("video.thumb[data-slot]")];
    if (!videos.length) return;
    for (let i = 0; i < 24; i++) {{
      try {{
        const r = await fetch("/media/{cid}/ready");
        const body = await r.json();
        let pending = false;
        for (const v of videos) {{
          if (body[v.dataset.slot]) v.hidden = false;
          else pending = true;
        }}
        if (!pending) return;
      }} catch (e) {{}}
      await new Promise((ok) => setTimeout(ok, 8000));
    }}
  }}
  revealClips();
</script>
</body>
</html>
"""


def _clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    return text[: max(0, n - 1)].rstrip() + "…"


def _utm(landing: str, campaign_id: str, variant: str) -> str:
    base = landing or __import__("os").environ.get("APP_URL") or ""
    if base and not base.startswith("http"):
        api = __import__("os").environ.get("APP_URL") or ""
        base = f"{api.rstrip('/')}{landing}"
    if not base:
        return ""
    sep = "&" if "?" in base else "?"
    return (
        f"{base}{sep}utm_source={quote(variant.split('_')[0])}"
        f"&utm_medium=paid&utm_campaign={quote(campaign_id)}&utm_content={quote(variant)}"
    )


def _lint(channel: dict[str, Any], headline: str, primary: str) -> dict[str, Any]:
    issues = []
    if any(w in (headline + primary).lower() for w in ("guaranteed", "miracle", "cure")):
        issues.append("claims")
    if channel["platform"] == "meta" and len(primary) > int(channel.get("primaryMax") or 125):
        issues.append("primary_too_long")
    return {"ok": not issues, "issues": issues}

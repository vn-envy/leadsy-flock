# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka-Adapt — one gated master → Meta / Google / WhatsApp kit. Never auto-posted."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote

from app import ledger
from app.design import resolve_theme
from app.derive import PIXEL_BOXES, download_name


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
        "proofClipSlot": "clip-proof-feed",
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
        "proofClipSlot": "clip-proof-square",
    },
    {
        "id": "meta_reel",
        "platform": "meta",
        "placement": "reel",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-indic",
        "clipSlotEn": "clip-en",
        "proofClipSlot": "clip-proof-indic",
        "proofClipSlotEn": "clip-proof-en",
    },
    {
        "id": "whatsapp_status",
        "platform": "whatsapp",
        "placement": "status",
        "aspect": "9:16",
        "primaryMax": 90,
        "headlineMax": 32,
        "stillSlot": "still-story",
        "clipSlot": "clip-indic",
        "clipSlotEn": "clip-en",
        "proofClipSlot": "clip-proof-indic",
        "proofClipSlotEn": "clip-proof-en",
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
        "proofClipSlot": "clip-proof-landscape",
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
    locale = inka.get("locale") or {}
    shelf = inka.get("shelf") or []
    landing = stella.get("url") or stella.get("landing") or ""
    shown = dict(campaign)
    resolved = str(inka.get("resolvedName") or "").strip()
    if resolved:
        shown["brief"] = {**(campaign.get("brief") or {}), "businessName": resolved}
    variants = [variant(ch, copy, landing, campaign_id) for ch in CHANNELS]
    page = render_kit(shown, copy, brand, variants, landing, locale=locale, shelf=shelf)
    path = f"/k/{campaign_id}"
    ledger.upsert_campaign(campaign_id, {"kitHtml": page, "kitPath": path, "locale": locale})
    return {
        "autopost": False,
        "note": "Ready to upload. Owner makes the final click on their own channels.",
        "landing": landing,
        "kit": path,
        "themeId": resolve_theme(brand).id,
        "locale": locale,
        "storyHook": copy.get("storyHook"),
        "variants": variants,
        "assets": inka.get("assets") or {},
    }


def variant(channel: dict[str, Any], copy: dict[str, Any], landing: str, campaign_id: str) -> dict[str, Any]:
    headline = _clip(str(copy.get("headline") or ""), int(channel.get("headlineMax") or 40))
    primary = _clip(str(copy.get("primaryText") or copy.get("subhead") or ""), int(channel.get("primaryMax") or 125))
    cta = str(copy.get("cta") or "Learn more")
    loc_h = _clip(str(copy.get("headlineLocalized") or ""), int(channel.get("headlineMax") or 40))
    loc_p = _clip(str(copy.get("primaryTextLocalized") or ""), int(channel.get("primaryMax") or 125))
    loc_cta = str(copy.get("ctaLocalized") or "")
    if channel.get("aspect") == "9:16" and loc_h:
        headline, primary, cta = loc_h, loc_p or primary, loc_cta or cta
    utm = _utm(landing, campaign_id, channel["id"])
    lint = _lint(channel, f"{headline} {loc_h} {loc_p}", primary)
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
        "headlineLocalized": loc_h,
        "primaryTextLocalized": loc_p,
        "ctaLocalized": loc_cta,
        "voIndic": str(copy.get("voIndic") or ""),
        "voEn": str(copy.get("voEn") or ""),
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
    if channel.get("clipSlotEn"):
        block["clipEn"] = f"/media/{campaign_id}/{channel['clipSlotEn']}"
        block["clipSlotEn"] = channel["clipSlotEn"]
    if channel.get("proofClipSlot"):
        block["proofClip"] = f"/media/{campaign_id}/{channel['proofClipSlot']}"
        block["proofClipSlot"] = channel["proofClipSlot"]
    if channel.get("proofClipSlotEn"):
        block["proofClipEn"] = f"/media/{campaign_id}/{channel['proofClipSlotEn']}"
        block["proofClipSlotEn"] = channel["proofClipSlotEn"]
    box_key = {"4:5": "feed", "1:1": "square", "9:16": "story", "1.91:1": "landscape"}.get(str(channel.get("aspect") or ""))
    if box_key and box_key in PIXEL_BOXES:
        pw, ph, _a = PIXEL_BOXES[box_key]
        block["width"] = pw
        block["height"] = ph
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
    locale: dict[str, Any] | None = None,
    shelf: list[dict[str, Any]] | None = None,
) -> str:
    theme = resolve_theme(brand)
    brief = campaign.get("brief") or {}
    business = html.escape(str(brief.get("businessName") or "Campaign"))
    geo = html.escape(str(brief.get("geo") or ""))
    cid = html.escape(str(campaign.get("id") or ""))
    headline = html.escape(str(copy.get("headline") or ""))
    sub = html.escape(str(copy.get("subhead") or ""))
    cta = html.escape(str(copy.get("cta") or "Learn more"))
    loc = locale or {}
    hook = html.escape(str(copy.get("storyHook") or ""))
    hook_l = html.escape(str(copy.get("storyHookLocalized") or ""))
    vo_l = html.escape(str(copy.get("voIndic") or ""))
    lang_label = html.escape(f"{loc.get('nativeName') or ''} ({loc.get('bcp47') or 'hi-IN'})".strip())
    shelf_rows = []
    for s in (shelf or [])[:6]:
        uri = html.escape(str(s.get("uri") or ""))
        title = html.escape(str(s.get("title") or "comparable"))
        ht = html.escape(str(s.get("hookType") or "craft"))
        shelf_rows.append(f'<li><span class="label">{ht}</span> <a href="{uri}">{title}</a></li>')
    shelf_html = (
        f"<ul class='shelf'>{''.join(shelf_rows)}</ul>" if shelf_rows else "<p class='muted'>No public comparables this run.</p>"
    )
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
        aspect = html.escape(str(v.get("aspect") or ""))
        pw = int(v.get("width") or 0)
        ph = int(v.get("height") or 0)
        size_label = f"{pw}×{ph}" if pw and ph else aspect

        def _frame(src: str, slot: str, label: str) -> str:
            if not src:
                return ""
            fname = html.escape(download_name(cid, slot))
            return (
                f'<figure class="frame" data-aspect="{aspect}">'
                f'<span class="badge">{html.escape(label)} · {size_label}</span>'
                f'<video class="thumb" data-slot="{html.escape(slot)}" src="{src}" '
                f'download="{fname}" muted playsinline controls loop hidden></video>'
                f'<a class="dl" href="{src}" download="{fname}">Save {size_label}</a>'
                f"</figure>"
            )

        if still:
            media_bits += (
                f'<figure class="frame" data-aspect="{aspect}">'
                f'<span class="badge">still · {size_label}</span>'
                f'<img class="thumb" src="{still}" alt="{vid} still" />'
                f"</figure>"
            )
        if clip:
            slot = str(v.get("clipSlot") or clip.rsplit("/", 1)[-1])
            media_bits += _frame(clip, slot, "place")
        clip_en = html.escape(str(v.get("clipEn") or ""))
        if clip_en:
            slot_en = str(v.get("clipSlotEn") or "clip-en")
            media_bits += _frame(clip_en, slot_en, "place EN")
        proof = html.escape(str(v.get("proofClip") or ""))
        if proof:
            media_bits += _frame(proof, str(v.get("proofClipSlot") or "clip-proof-feed"), "proof")
        proof_en = html.escape(str(v.get("proofClipEn") or ""))
        if proof_en:
            media_bits += _frame(proof_en, str(v.get("proofClipSlotEn") or "clip-proof-en"), "proof EN")
        if str(v.get("aspect") or "") == "9:16":
            cap = html.escape(f"/media/{cid}/clip-captioned")
            media_bits += _frame(cap, "clip-captioned", "captions")
        rsa = ""
        if v.get("headlines"):
            lines = "".join(f"<li>{html.escape(str(x))}</li>" for x in v["headlines"])
            rsa = f"<p class='label'>RSA headlines</p><ul>{lines}</ul>"
            if v.get("description"):
                rsa += f"<p class='label'>Description</p><p class='copy'>{html.escape(str(v['description']))}</p>"
        loc_block = ""
        vo = html.escape(str(v.get("voIndic") or copy.get("voIndic") or ""))
        vo_en = html.escape(str(v.get("voEn") or copy.get("voEn") or ""))
        if str(v.get("aspect") or "") == "9:16":
            bits = []
            if vo_en:
                bits.append(f"<p class='label'>VO English</p><p class='copy'>{vo_en}</p>")
            if vo:
                bits.append(f"<p class='label'>VO · {lang_label}</p><p class='copy'>{vo}</p>")
            loc_block = "".join(bits)
        elif v.get("headlineLocalized") and str(v.get("aspect") or "") != "9:16":
            loc_block = (
                f"<p class='label'>{lang_label}</p>"
                f"<p class='copy'>{html.escape(str(v.get('headlineLocalized')))}</p>"
            )
        cards.append(
            f"""<article class="card" data-id="{vid}">
  <p class="kicker">{html.escape(str(kind))} · {aspect}</p>
  <h2>{vid}</h2>
  <div class="thumbs">{media_bits or "<p class='muted'>Text only</p>"}</div>
  <p class="label">Headline</p><p class="copy">{h}</p>
  <p class="label">Primary</p><p class="copy">{p}</p>
  {loc_block}
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
    .frame {{
      position: relative; width: 100%; background: var(--bg);
      border: 1px solid var(--line); border-radius: .6rem; overflow: hidden;
    }}
    .frame[data-aspect="4:5"] {{ aspect-ratio: 4 / 5; }}
    .frame[data-aspect="1:1"] {{ aspect-ratio: 1 / 1; }}
    .frame[data-aspect="9:16"] {{ aspect-ratio: 9 / 16; }}
    .frame[data-aspect="1.91:1"] {{ aspect-ratio: 1.91 / 1; }}
    .frame .thumb {{
      width: 100%; height: 100%; object-fit: contain; display: block;
      background: var(--bg); max-height: none;
    }}
    .frame .badge {{
      position: absolute; top: .4rem; left: .4rem; z-index: 1;
      font-size: .65rem; letter-spacing: .08em; text-transform: uppercase;
      background: var(--surface); color: var(--muted); border: 1px solid var(--line);
      border-radius: .35rem; padding: .15rem .35rem;
    }}
    .frame .dl {{
      display: block; font-size: .72rem; padding: .35rem .5rem; color: var(--accent);
    }}
    video.thumb[hidden] {{ display: none; }}
    .label {{ font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin: .7rem 0 .2rem; }}
    .copy {{ margin: 0; font-size: .92rem; line-height: 1.45; word-break: break-word; }}
    .utm {{ font-size: .78rem; color: var(--muted); }}
    .muted {{ color: var(--muted); font-size: .85rem; }}
    ul.shelf {{ margin: .4rem 0 0 1.1rem; padding: 0; }}
    ul.shelf .label {{ margin: 0 .4rem 0 0; display: inline; }}
    .note {{ margin-top: 2rem; color: var(--muted); font-size: .85rem; }}
  </style>
</head>
<body>
<main>
  <p class="kicker">{business} · {geo} · {lang_label} · asset kit</p>
  <h1>{headline or "Launch kit"}</h1>
  <p class="lede">{html.escape(str(copy.get("storyHook") or sub))} Remix a live shelf trope — do not fake UGC, do not clone pixels. Stills start from this shop's own photos, listing, menu, or site when we have them; Gemini only cleans or fills gaps. Copy stays off Veo. We do not autopost.
  <a href="{land_href}">Consent landing</a>.</p>
  <p class="label">Story hook · {lang_label}</p>
  <p class="copy">{hook_l or hook or sub}</p>
  <p class="label">Spoken line · English</p>
  <p class="copy">{html.escape(str(copy.get("voEn") or ""))}</p>
  <p class="label">Spoken line · {lang_label}</p>
  <p class="copy">{vo_l or html.escape(str(copy.get("voEn") or ""))}</p>
  <p class="label">Comparables this run</p>
  {shelf_html}
  <div class="grid">
    {cards_html}
  </div>
  <p class="note">Each card is the declared channel file: 1080×1350 feed, 1080×1080 square, 1080×1920 Reels/WhatsApp, 1200×628 Google display. Place film is the room; proof film is the dish / result / SKU from this shop's own photos. English and local-language VO are muxed onto the same picture. Captions are centre safe-zone, 9:16 only. We do not autopost.</p>
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

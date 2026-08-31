# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Flock-branded paste kit. Same roost language as /, never a form stack."""

from __future__ import annotations

import html
from typing import Any

from app import ledger
from app.derive import download_name
from app.run_ui import ASSET, _cast_html, _src


def render_from_campaign(campaign_id: str, campaign: dict[str, Any]) -> str | None:
    receipts = ledger.list_receipts(campaign_id) if hasattr(ledger, "list_receipts") else []
    if not isinstance(receipts, list):
        receipts = []
    inka = _step(receipts, "inka")
    adkit = _step(receipts, "ad_kit")
    stella = _step(receipts, "stella")
    variants = adkit.get("variants") or []
    if not variants:
        return None
    copy = inka.get("copy") or {}
    brand = inka.get("brandSpec") or {}
    locale = inka.get("locale") or campaign.get("locale") or {}
    shelf = inka.get("shelf") or []
    landing = campaign.get("landingPath") or stella.get("url") or stella.get("landing") or f"/l/{campaign_id}"
    shown = dict(campaign)
    shown["id"] = campaign_id
    resolved = str(inka.get("resolvedName") or "").strip()
    if resolved:
        shown["brief"] = {**(campaign.get("brief") or {}), "businessName": resolved}
    return render_kit(shown, copy, brand, variants, str(landing), locale=locale, shelf=shelf)


def render_kit(
    campaign: dict[str, Any],
    copy: dict[str, Any],
    brand: dict[str, Any],
    variants: list[dict[str, Any]],
    landing: str,
    locale: dict[str, Any] | None = None,
    shelf: list[dict[str, Any]] | None = None,
) -> str:
    del brand  # flock chrome is the hackathon kit, not the shop theme tokens
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
    vo_en = html.escape(str(copy.get("voEn") or ""))
    lang_label = html.escape(f"{loc.get('nativeName') or ''} ({loc.get('bcp47') or 'hi-IN'})".strip())
    land_href = html.escape(landing or f"/l/{cid}")
    hero = _src("hero")
    shelf_bits = []
    for s in (shelf or [])[:6]:
        uri = html.escape(str(s.get("uri") or ""))
        title = html.escape(str(s.get("title") or "comparable"))
        ht = html.escape(str(s.get("hookType") or "craft"))
        shelf_bits.append(f'<a class="chip" href="{uri}" target="_blank" rel="noopener noreferrer"><span>{ht}</span>{title}</a>')
    shelf_html = "".join(shelf_bits) or '<p class="muted">No public comparables this run.</p>'
    cards = []
    for v in variants:
        cards.append(_card(v, cid, copy, cta, lang_label))
    cards_html = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en" data-theme="flock">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Kit · {business}</title>
  <link rel="stylesheet" href="{ASSET}/kit.css?v=submit2"/>
  <style>video.thumb[hidden] {{ display: none; }}</style>
</head>
<body>
<section class="wash" style="background-image:url('{hero}')">
  <div class="grain" aria-hidden="true"></div>
  <div class="veil"></div>
  <div class="cast">{_cast_html()}</div>
</section>
<main class="sheet">
  <header class="mast">
    <a class="word" href="/" target="_top">Leadsy Flock</a>
    <nav>
      <a href="/dash" target="_top">observatory</a>
      <a href="/architecture" target="_top">architecture</a>
      <a href="{land_href}" target="_top">landing</a>
      <span class="here">kit</span>
    </nav>
  </header>
  <p class="quiet">{business} · {geo} · {lang_label}</p>
  <h1>{headline or "Paste kit"}</h1>
  <p class="lede">{html.escape(str(copy.get("storyHook") or sub))}. Remix a live shelf trope — do not fake UGC, do not clone pixels. Stills start from this shop's own photos, listing, menu, or site when we have them; Gemini only cleans or fills gaps. Copy stays off Veo. We do not autopost.</p>
  <div class="lines">
    <div class="quiet-card">
      <p class="label">Story hook · {lang_label}</p>
      <p class="copy">{hook_l or hook or sub}</p>
    </div>
    <div class="quiet-card">
      <p class="label">Spoken line · English</p>
      <p class="copy">{vo_en}</p>
    </div>
    <div class="quiet-card">
      <p class="label">Spoken line · {lang_label}</p>
      <p class="copy">{vo_l or vo_en}</p>
    </div>
  </div>
  <p class="label">Comparables this run</p>
  <div class="chips">{shelf_html}</div>
  <div class="bento">
    {cards_html}
  </div>
  <p class="note">Each card is the declared channel file: 1080×1350 feed, 1080×1080 square, 1080×1920 Reels/WhatsApp, 1200×628 Google display. Place film is the room; proof film is the dish / result / SKU from this shop's own photos. English and local-language VO are muxed onto the same picture. Captions are centre safe-zone, 9:16 only. We do not autopost.</p>
</main>
<script>
  if (window.self !== window.top) document.body.classList.add("embed");
  async function revealClips() {{
    const videos = [...document.querySelectorAll("video.thumb[data-slot]")];
    if (!videos.length) return;
    for (let i = 0; i < 24; i++) {{
      try {{
        const r = await fetch("/media/{cid}/ready");
        const body = await r.json();
        let pending = false;
        for (const v of videos) {{
          if (body[v.dataset.slot]) {{
            v.hidden = false;
            const slot = v.closest(".film-slot");
            if (slot) {{
              slot.classList.add("on");
              const link = slot.querySelector(".film-link");
              if (link) link.hidden = false;
            }}
          }} else pending = true;
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


def _step(receipts: list[dict[str, Any]], step: str) -> dict[str, Any]:
    for rec in receipts:
        if rec.get("step") == step:
            payload = rec.get("payload") or {}
            return payload if isinstance(payload, dict) else {}
    return {}


def _frame(src: str, slot: str, label: str, aspect: str, size_label: str, cid: str) -> str:
    del aspect  # films sit in a compact row; stills keep the ratio
    if not src:
        return ""
    fname = html.escape(download_name(cid, slot))
    return (
        f'<div class="film-slot">'
        f'<video class="thumb" data-slot="{html.escape(slot)}" src="{src}" '
        f'download="{fname}" muted playsinline controls loop hidden></video>'
        f'<a class="film-link" href="{src}" download="{fname}" hidden '
        f'aria-label="Save {html.escape(label)} {html.escape(size_label)}">'
        f"Save {html.escape(size_label)}</a>"
        f"</div>"
    )


def _card(
    v: dict[str, Any],
    cid: str,
    copy: dict[str, Any],
    cta: str,
    lang_label: str,
) -> str:
    vid = html.escape(str(v.get("id") or ""))
    aspect = html.escape(str(v.get("aspect") or ""))
    still = html.escape(str(v.get("still") or ""))
    h = html.escape(str(v.get("headline") or ""))
    p = html.escape(str(v.get("primaryText") or ""))
    u = html.escape(str(v.get("utmUrl") or ""))
    kind = "organic" if v.get("organic") else v.get("platform")
    pw = int(v.get("width") or 0)
    ph = int(v.get("height") or 0)
    size_label = f"{pw}×{ph}" if pw and ph else aspect
    still_html = ""
    if still:
        still_html = (
            f'<figure class="still" data-aspect="{aspect}">'
            f'<span class="badge">still · {size_label}</span>'
            f'<img class="thumb" src="{still}" alt="{vid} still" />'
            f"</figure>"
        )
    films = []
    clip = html.escape(str(v.get("clip") or ""))
    if clip:
        slot = str(v.get("clipSlot") or clip.rsplit("/", 1)[-1])
        films.append(_frame(clip, slot, "place", aspect, size_label, cid))
    clip_en = html.escape(str(v.get("clipEn") or ""))
    if clip_en:
        films.append(_frame(clip_en, str(v.get("clipSlotEn") or "clip-en"), "place EN", aspect, size_label, cid))
    proof = html.escape(str(v.get("proofClip") or ""))
    if proof:
        films.append(_frame(proof, str(v.get("proofClipSlot") or "clip-proof-feed"), "proof", aspect, size_label, cid))
    proof_en = html.escape(str(v.get("proofClipEn") or ""))
    if proof_en:
        films.append(_frame(proof_en, str(v.get("proofClipSlotEn") or "clip-proof-en"), "proof EN", aspect, size_label, cid))
    if str(v.get("aspect") or "") == "9:16":
        cap = html.escape(f"/media/{cid}/clip-captioned")
        films.append(_frame(cap, "clip-captioned", "captions", aspect, size_label, cid))
    media = still_html
    if films:
        media += f'<div class="films">{"".join(films)}</div>'
    if not media:
        media = "<p class='muted'>Text only</p>"
    rsa = ""
    if v.get("headlines"):
        lines = "".join(f"<li>{html.escape(str(x))}</li>" for x in v["headlines"])
        rsa = f"<p class='label'>RSA headlines</p><ul class='rsa'>{lines}</ul>"
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
    return f"""<article class="card" data-id="{vid}">
  <header class="head">
    <p class="kicker">{html.escape(str(kind))} · {aspect} · {size_label}</p>
    <h2>{vid}</h2>
  </header>
  <div class="media">{media or "<p class='muted'>Text only</p>"}</div>
  <div class="copyblock">
  <p class="label">Headline</p><p class="copy">{h}</p>
  <p class="label">Primary</p><p class="copy">{p}</p>
  {loc_block}
  {rsa}
  <p class="label">UTM</p><p class="copy utm">{u}</p>
  <p class="muted">CTA: {html.escape(str(v.get("cta") or cta))}</p>
  </div>
</article>"""

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Owner studio — the delivery room. Paste kit, UTMs, films. No autopost."""

from __future__ import annotations

import hmac
import html
from collections import Counter
from typing import Any

from app import ledger, media
from app.cost import estimate_campaign, owner_cost_blurb
from app.design import resolve_theme
from app.derive import PIXEL_BOXES, download_name


def check_key(campaign: dict[str, Any], provided: str | None) -> bool:
    expected = str(campaign.get("studioKey") or "")
    if not expected:
        return False
    return hmac.compare_digest(expected, provided or "")


def studio_payload(campaign_id: str, campaign: dict[str, Any]) -> dict[str, Any]:
    receipts = ledger.list_receipts(campaign_id) if hasattr(ledger, "list_receipts") else []
    if not isinstance(receipts, list):
        receipts = []
    hits = ledger.list_events(campaign_id, kind="landing_hit") if hasattr(ledger, "list_events") else []
    if not isinstance(hits, list):
        hits = []
    est = estimate_campaign(campaign_id, receipts)
    blurb = owner_cost_blurb(est)
    inka = _payload(receipts, "inka")
    adkit = _payload(receipts, "ad_kit")
    copy = inka.get("copy") or {}
    variants = adkit.get("variants") or []
    ready = {}
    try:
        ready = {
            slot: media.campaign_asset_exists(campaign_id, names)
            for slot, names in media.MEDIA_SLOTS.items()
        }
    except Exception:  # noqa: BLE001
        ready = {}
    utm_rows = _utm_table(variants, hits)
    return {
        "id": campaign_id,
        "status": campaign.get("status"),
        "brief": campaign.get("brief") or {},
        "copy": copy,
        "brand": inka.get("brandSpec") or {},
        "locale": inka.get("locale") or campaign.get("locale") or {},
        "variants": variants,
        "utm": utm_rows,
        "hits": _hit_summary(hits),
        "cost": blurb,
        "ready": ready,
        "landingPath": campaign.get("landingPath") or f"/l/{campaign_id}",
        "kitPath": campaign.get("kitPath") or f"/k/{campaign_id}",
        "autopost": False,
        "pixels": {k: {"w": v[0], "h": v[1]} for k, v in PIXEL_BOXES.items()},
    }


def render_html(campaign_id: str, campaign: dict[str, Any]) -> str:
    data = studio_payload(campaign_id, campaign)
    brief = data["brief"]
    business = html.escape(str(brief.get("businessName") or "Campaign"))
    geo = html.escape(str(brief.get("geo") or ""))
    copy = data["copy"]
    headline = html.escape(str(copy.get("headline") or business))
    theme = resolve_theme(data.get("brand") or {})
    cost = data["cost"]
    quoted = html.escape(str(cost.get("quotedInr") or "—"))
    band = html.escape(str(cost.get("productionBand") or ""))
    hit = data["hits"]
    hit_n = int(hit.get("count") or 0)
    variants = data["variants"] or []
    utm_rows = data["utm"]
    loc = data["locale"]
    lang = html.escape(str(loc.get("nativeName") or loc.get("bcp47") or "hi-IN"))
    cards = []
    for v in variants:
        vid = html.escape(str(v.get("id") or ""))
        aspect = html.escape(str(v.get("aspect") or ""))
        h = html.escape(str(v.get("headline") or ""))
        p = html.escape(str(v.get("primaryText") or ""))
        u = html.escape(str(v.get("utmUrl") or ""))
        still = html.escape(str(v.get("still") or ""))
        clip = html.escape(str(v.get("clip") or ""))
        pw = int(v.get("width") or 0)
        ph = int(v.get("height") or 0)
        size = f"{pw}×{ph}" if pw and ph else aspect
        media_bits = ""
        if still:
            media_bits += f'<img class="thumb" src="{still}" alt="{vid} still"/>'
        if clip:
            slot = html.escape(str(v.get("clipSlot") or "clip"))
            fname = html.escape(download_name(campaign_id, slot))
            media_bits += (
                f'<video class="thumb" data-slot="{slot}" src="{clip}" '
                f'download="{fname}" muted playsinline controls loop hidden></video>'
                f'<a class="dl" href="{clip}" download="{fname}">Save {size}</a>'
            )
        cards.append(
            f"""<article class="card">
  <p class="kicker">{html.escape(str(v.get("platform") or ""))} · {aspect} · {size}</p>
  <h2>{vid}</h2>
  <div class="thumbs">{media_bits or "<p class='muted'>Text only — paste the RSA lines.</p>"}</div>
  <p class="label">Headline</p><p class="copy">{h}</p>
  <p class="label">Primary</p><p class="copy">{p}</p>
  <p class="label">UTM (paste this URL into Ads Manager)</p>
  <p class="copy utm">{u}</p>
</article>"""
        )
    utm_html = "".join(
        f"<tr><td>{html.escape(r['content'])}</td><td>{html.escape(r['source'])}</td>"
        f"<td>{r['hits']}</td></tr>"
        for r in utm_rows
    ) or "<tr><td class='muted' colspan='3'>No tracked clicks yet. Open a UTM from the kit to test.</td></tr>"
    cards_html = "\n".join(cards) or "<p class='muted'>Kit still rendering.</p>"
    return f"""<!doctype html>
<html lang="en" data-theme="{html.escape(theme.id)}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Studio · {business}</title>
  <style>
    :root {{ {theme.css_vars()} }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--fg); font-family:system-ui,sans-serif; }}
    main {{ width:min(72rem, calc(100% - 2rem)); margin:0 auto; padding:2.5rem 0 4rem; }}
    .kicker {{ letter-spacing:.16em; font-size:.75rem; text-transform:uppercase; color:var(--accent); font-weight:650; margin:0 0 .6rem; }}
    h1 {{ font-family:Georgia,serif; font-weight:500; font-size:clamp(1.6rem,4vw,2.4rem); margin:0 0 .4rem; }}
    .lede {{ color:var(--muted); max-width:42rem; line-height:1.55; }}
    a {{ color:var(--accent); }}
    .grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr)); margin-top:1.5rem; }}
    .card, .panel {{
      background:var(--surface); border:1px solid var(--line);
      border-radius:1rem; padding:1rem 1rem 1.1rem;
    }}
    .thumbs {{ display:grid; gap:.5rem; margin-bottom:.85rem; }}
    .thumb {{ width:100%; border-radius:.6rem; background:var(--bg); border:1px solid var(--line); }}
    video.thumb[hidden] {{ display:none; }}
    .label {{ font-size:.68rem; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin:.7rem 0 .2rem; }}
    .copy {{ margin:0; font-size:.92rem; line-height:1.45; word-break:break-word; }}
    .utm {{ font-size:.78rem; color:var(--muted); }}
    .muted {{ color:var(--muted); font-size:.85rem; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ text-align:left; padding:.5rem .3rem; border-bottom:1px solid var(--line); }}
    .dl {{ font-size:.78rem; }}
    .note {{ margin-top:1.5rem; color:var(--muted); font-size:.85rem; }}
  </style>
</head>
<body>
<main>
  <p class="kicker">{business} · {geo} · {lang} · delivery room</p>
  <h1>{headline}</h1>
  <p class="lede">This page is the delivery room. Paste into your own Ads Manager.
  We do not autopost. <a href="{html.escape(str(data['kitPath']))}">Full kit</a> ·
  <a href="{html.escape(str(data['landingPath']))}">Consent landing</a>.</p>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))">
    <section class="panel">
      <p class="kicker">Quoted vs production</p>
      <p class="copy">You were quoted <strong>₹{quoted}</strong>.</p>
      <p class="copy">Our cost to run this kit: {band}</p>
      <p class="muted">{html.escape(str(cost.get("note") or ""))}</p>
    </section>
    <section class="panel">
      <p class="kicker">Landing hits</p>
      <p class="copy">{hit_n} tracked UTM click{"s" if hit_n != 1 else ""}.</p>
      <p class="muted">Open a kit UTM on a second device to prove the path. Consent is still a checkbox on the landing.</p>
    </section>
  </div>
  <p class="label">UTM tracking</p>
  <table>
    <thead><tr><th>utm_content</th><th>utm_source</th><th>Hits</th></tr></thead>
    <tbody>{utm_html}</tbody>
  </table>
  <div class="grid">
    {cards_html}
  </div>
  <p class="note">Ratios: 1080×1350 feed, 1080×1080 square, 1080×1920 story, 1200×628 display.
  English + Indic VO on the same picture. No autopost.</p>
</main>
<script>
  async function reveal() {{
    const videos = [...document.querySelectorAll("video.thumb[data-slot]")];
    if (!videos.length) return;
    for (let i = 0; i < 24; i++) {{
      try {{
        const r = await fetch("/media/{html.escape(campaign_id)}/ready");
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
  reveal();
</script>
</body>
</html>
"""


def _payload(receipts: list[dict[str, Any]], step: str) -> dict[str, Any]:
    for rec in receipts:
        if rec.get("step") == step:
            payload = rec.get("payload") or {}
            return payload if isinstance(payload, dict) else {}
    return {}


def _utm_table(variants: list[dict[str, Any]], hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for hit in hits:
        detail = hit.get("detail") if isinstance(hit, dict) else None
        if not isinstance(detail, dict):
            continue
        content = str(detail.get("utm_content") or detail.get("utmContent") or "unknown")
        source = str(detail.get("utm_source") or detail.get("utmSource") or "unknown")
        counts[(content, source)] += 1
    rows = []
    seen: set[tuple[str, str]] = set()
    for v in variants:
        content = str(v.get("id") or "")
        source = str(v.get("platform") or (content.split("_")[0] if content else ""))
        key = (content, source)
        seen.add(key)
        rows.append({"content": content, "source": source, "hits": counts.get(key, 0), "utmUrl": v.get("utmUrl")})
    for key, n in counts.items():
        if key in seen:
            continue
        rows.append({"content": key[0], "source": key[1], "hits": n, "utmUrl": ""})
    return rows


def _hit_summary(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return {"count": len(hits)}

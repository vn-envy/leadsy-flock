# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Stella — consent-first landing page served by flock-api."""

from __future__ import annotations

import html
from typing import Any

from app import ledger
from app.design import resolve_theme
from app.settings import load_settings


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    copy = inka.get("copy") or {}
    brand = inka.get("brandSpec") or (ledger.get_receipt(campaign_id, "scout") or {}).get("payload", {}).get("brandSpec") or {}
    still = (inka.get("assets") or {}).get("still") or {}
    still_src = f"/media/{campaign_id}/still" if still.get("ok") else ""
    clip_src = f"/media/{campaign_id}/clip"
    jingle_src = f"/media/{campaign_id}/jingle"
    page = render_html(campaign, copy, brand, still_src=still_src, clip_src=clip_src, jingle_src=jingle_src)
    s = load_settings()
    base = __import__("os").environ.get("APP_URL") or f"https://flock-api.{s.region}.run.app"
    path = f"/l/{campaign_id}"
    theme = resolve_theme(brand)
    ledger.upsert_campaign(
        campaign_id,
        {
            "landingHtml": page,
            "landingPath": path,
            "stillPath": still_src or None,
            "themeId": theme.id,
        },
    )
    return {
        "landing": path,
        "url": f"{base.rstrip('/')}{path}",
        "still": still_src or None,
        "clip": clip_src,
        "jingle": jingle_src,
        "themeId": theme.id,
        "consentCapture": True,
        "headline": copy.get("headline"),
    }


def render_html(
    campaign: dict[str, Any],
    copy: dict[str, Any],
    brand: dict[str, Any],
    still_src: str = "",
    clip_src: str = "",
    jingle_src: str = "",
) -> str:
    brief = campaign.get("brief") or {}
    business = html.escape(str(brief.get("businessName") or "Our studio"))
    geo = html.escape(str(brief.get("geo") or ""))
    headline = html.escape(str(copy.get("headline") or f"{business} in {geo}"))
    sub = html.escape(str(copy.get("subhead") or copy.get("primaryText") or "Tell us you want to hear from us."))
    cta = html.escape(str(copy.get("cta") or "Count me in"))
    theme = resolve_theme(brand)
    vars_css = theme.css_vars()
    cid = html.escape(str(campaign.get("id") or ""))
    hero = ""
    if still_src:
        src = html.escape(still_src)
        hero = f'<img class="hero" id="still" src="{src}" alt="{business} campaign still" />'
    clip_tag = ""
    if clip_src:
        csrc = html.escape(clip_src)
        poster = html.escape(still_src) if still_src else ""
        clip_tag = (
            f'<video class="hero" id="clip" src="{csrc}" poster="{poster}" '
            f'muted playsinline autoplay loop hidden></video>'
        )
    jingle_tag = ""
    if jingle_src:
        jsrc = html.escape(jingle_src)
        jingle_tag = f'<audio id="jingle" src="{jsrc}" controls hidden></audio>'
    return f"""<!doctype html>
<html lang="en" data-theme="{html.escape(theme.id)}" data-color-scheme="{theme.scheme}">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="color-scheme" content="{theme.scheme}"/>
  <title>{business}</title>
  <style>
    :root {{ {vars_css} }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; min-height: 100%; }}
    body {{
      display: grid; place-items: center;
      font-family: system-ui, "Segoe UI", sans-serif;
      background: var(--bg); color: var(--fg);
    }}
    main {{
      width: min(38rem, calc(100% - 2.5rem));
      padding: 3rem 0 4.5rem;
    }}
    p.kicker {{
      letter-spacing: 0.16em; font-size: 0.8rem; text-transform: uppercase;
      color: var(--accent); margin: 0 0 1.1rem; font-weight: 650;
    }}
    h1 {{
      font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
      font-size: clamp(1.85rem, 4.6vw, 2.85rem); line-height: 1.18;
      font-weight: 500; margin: 0 0 0.85rem; color: var(--fg);
    }}
    .hero {{
      width: 100%; aspect-ratio: 16 / 9; object-fit: cover;
      border-radius: 0.85rem; margin: 0 0 1.35rem;
      background: var(--surface); border: 1px solid var(--line);
      display: block;
    }}
    .hero[hidden], audio[hidden] {{ display: none; }}
    .sub {{
      line-height: 1.6; color: var(--muted); max-width: 34rem;
      margin: 0; font-size: 1.02rem;
    }}
    form {{
      margin-top: 2rem; display: grid; gap: 0.8rem;
    }}
    input[type="text"], input:not([type]), input[type="email"] {{
      background: var(--surface); border: 1px solid var(--line); color: var(--fg);
      border-radius: 0.7rem; padding: 0.9rem 1rem; font: inherit;
    }}
    input::placeholder {{ color: var(--muted); opacity: 0.9; }}
    input:focus-visible, button:focus-visible, label.check:focus-within {{
      outline: 2px solid var(--accent); outline-offset: 2px;
    }}
    label.check {{
      display: flex; gap: 0.65rem; align-items: flex-start;
      font-size: 0.95rem; line-height: 1.45; color: var(--fg);
    }}
    label.check input {{ margin-top: 0.2rem; accent-color: var(--accent); }}
    button {{
      justify-self: start; background: var(--accent); color: var(--accent-fg);
      border: 0; border-radius: 999px; padding: 0.85rem 1.45rem;
      font-weight: 650; cursor: pointer; min-height: 2.75rem; font: inherit;
    }}
    button:disabled {{ opacity: 0.55; cursor: wait; }}
    .note {{ font-size: 0.82rem; color: var(--muted); margin: 0.15rem 0 0; }}
    .ok {{ color: var(--accent); }}
    audio {{ width: 100%; margin-top: 0.75rem; }}
    @media (max-width: 640px) {{
      main {{ width: min(38rem, calc(100% - 1.75rem)); padding: 2rem 0 3.5rem; }}
    }}
  </style>
</head>
<body>
  <main>
    <p class="kicker">{business} · {geo} · consent first</p>
    {hero}
    {clip_tag}
    <h1>{headline}</h1>
    <p class="sub">{sub}</p>
    {jingle_tag}
    <form id="optin">
      <input name="name" placeholder="Your name" required maxlength="80" autocomplete="name"/>
      <input name="contact" placeholder="Email or WhatsApp" required maxlength="120" autocomplete="email"/>
      <label class="check">
        <input type="checkbox" name="consent" required/>
        <span>I want {business} to contact me about this. Discovery is not consent — this box is.</span>
      </label>
      <button type="submit">{cta}</button>
      <p class="note">We will not email anyone who did not opt in here. No autoposting to ads.</p>
      <p id="status" class="note"></p>
    </form>
  </main>
  <script>
    const form = document.getElementById("optin");
    const status = document.getElementById("status");
    form.addEventListener("submit", async (e) => {{
      e.preventDefault();
      const fd = new FormData(form);
      if (!fd.get("consent")) return;
      const btn = form.querySelector("button");
      btn.disabled = true;
      status.textContent = "Saving your yes…";
      try {{
        const res = await fetch("/v1/consents", {{
          method: "POST",
          headers: {{ "content-type": "application/json" }},
          body: JSON.stringify({{
            campaignId: "{cid}",
            name: fd.get("name"),
            contact: fd.get("contact"),
            consent: true,
            source: "landing"
          }})
        }});
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || body.error || res.status);
        status.className = "ok";
        status.textContent = "You're in. We'll only use this to follow up about {business}.";
        form.reset();
      }} catch (err) {{
        status.textContent = String(err.message || err);
        btn.disabled = false;
      }}
    }});
    async function revealWhenReady(kind, onReady, tries) {{
      for (let i = 0; i < tries; i++) {{
        try {{
          const r = await fetch("/media/{cid}/ready");
          const body = await r.json();
          if (body[kind]) {{
            onReady();
            return;
          }}
        }} catch (e) {{}}
        await new Promise((ok) => setTimeout(ok, 8000));
      }}
    }}
    const clip = document.getElementById("clip");
    const still = document.getElementById("still");
    revealWhenReady("clip", () => {{
      if (clip) {{
        clip.hidden = false;
        if (still) still.hidden = true;
        clip.play().catch(() => {{}});
      }}
    }}, 24);
    const jingle = document.getElementById("jingle");
    revealWhenReady("jingle", () => {{
      if (jingle) jingle.hidden = false;
    }}, 8);
  </script>
</body>
</html>
"""

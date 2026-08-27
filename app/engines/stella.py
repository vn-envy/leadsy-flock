# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Stella — consent-first landing page served by flock-api."""

from __future__ import annotations

import html
from typing import Any

from app import ledger
from app.settings import load_settings


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = campaign.get("id") or ""
    inka = (ledger.get_receipt(campaign_id, "inka") or {}).get("payload") or {}
    copy = inka.get("copy") or {}
    brand = inka.get("brandSpec") or (ledger.get_receipt(campaign_id, "scout") or {}).get("payload", {}).get("brandSpec") or {}
    still = (inka.get("assets") or {}).get("still") or {}
    still_src = f"/media/{campaign_id}/still" if still.get("ok") else ""
    page = render_html(campaign, copy, brand, still_src=still_src)
    s = load_settings()
    base = __import__("os").environ.get("APP_URL") or f"https://flock-api.{s.region}.run.app"
    path = f"/l/{campaign_id}"
    ledger.upsert_campaign(
        campaign_id,
        {"landingHtml": page, "landingPath": path, "stillPath": still_src or None},
    )
    return {
        "landing": path,
        "url": f"{base.rstrip('/')}{path}",
        "still": still_src or None,
        "consentCapture": True,
        "headline": copy.get("headline"),
    }


def render_html(
    campaign: dict[str, Any],
    copy: dict[str, Any],
    brand: dict[str, Any],
    still_src: str = "",
) -> str:
    brief = campaign.get("brief") or {}
    business = html.escape(str(brief.get("businessName") or "Our studio"))
    geo = html.escape(str(brief.get("geo") or ""))
    headline = html.escape(str(copy.get("headline") or f"{business} in {geo}"))
    sub = html.escape(str(copy.get("subhead") or copy.get("primaryText") or "Tell us you want to hear from us."))
    cta = html.escape(str(copy.get("cta") or "Count me in"))
    palette = brand.get("palette") or ["#c4a574", "#0f1419", "#f4efe6"]
    gold = html.escape(str(palette[0]))
    ink = html.escape(str(palette[1] if len(palette) > 1 else "#0f1419"))
    paper = html.escape(str(palette[2] if len(palette) > 2 else "#f4efe6"))
    cid = html.escape(str(campaign.get("id") or ""))
    hero = ""
    if still_src:
        src = html.escape(still_src)
        hero = f'<img class="hero" src="{src}" alt="{business} campaign still" />'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{business}</title>
  <style>
    :root {{ --gold:{gold}; --ink:{ink}; --paper:{paper}; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--ink); color: var(--paper);
    }}
    main {{
      width: min(40rem, calc(100% - 2.5rem));
      padding: 2.5rem 0 4rem;
    }}
    p.kicker {{
      letter-spacing: 0.22em; font-size: 0.72rem; text-transform: uppercase;
      color: var(--gold); font-family: system-ui, sans-serif; margin: 0 0 1rem;
    }}
    h1 {{ font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1.15; font-weight: 500; margin: 0 0 1rem; }}
    .hero {{
      width: 100%; aspect-ratio: 16 / 9; object-fit: cover;
      border-radius: 1rem; margin: 0 0 1.25rem; background: #1a2220;
    }}
    .sub {{ font-family: system-ui, sans-serif; line-height: 1.55; color: #d8d0c4; max-width: 34rem; }}
    form {{
      margin-top: 2rem; display: grid; gap: 0.75rem;
      font-family: system-ui, sans-serif;
    }}
    input {{
      background: transparent; border: 1px solid #3a433c; color: var(--paper);
      border-radius: 0.75rem; padding: 0.85rem 1rem; font: inherit;
    }}
    label.check {{ display: flex; gap: 0.6rem; align-items: flex-start; font-size: 0.92rem; line-height: 1.4; }}
    button {{
      justify-self: start; background: var(--gold); color: var(--ink);
      border: 0; border-radius: 999px; padding: 0.75rem 1.4rem; font-weight: 600; cursor: pointer;
    }}
    button:disabled {{ opacity: 0.5; cursor: wait; }}
    .note {{ font-size: 0.8rem; color: #9a9286; }}
    .ok {{ color: var(--gold); }}
  </style>
</head>
<body>
  <main>
    <p class="kicker">{business} · {geo} · consent first</p>
    {hero}
    <h1>{headline}</h1>
    <p class="sub">{sub}</p>
    <form id="optin">
      <input name="name" placeholder="Your name" required maxlength="80"/>
      <input name="contact" placeholder="Email or WhatsApp" required maxlength="120"/>
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
  </script>
</body>
</html>
"""

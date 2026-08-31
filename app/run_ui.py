# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Single flamingo-flock stage: listing in, kit on the same canvas. Not a form."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from app.seed import DEMO_SHOP

ASSET = "/assets/flock"
_DIR = Path(__file__).resolve().parent / "static" / "flock"
CAST = (
    ("flo", "Flo", "Director", "flo"),
    ("bri", "Bri", "Strategist", "bri"),
    ("scout", "Scout", "Tracker", "scout"),
    ("inka", "Inka", "Artist", "inka"),
    ("stella", "Stella", "Host", "stella"),
)
PATH_STEPS = (
    ("scout", "Scout"),
    ("inka", "Inka"),
    ("inka_harvest", "Harvest"),
    ("creative_gate", "Gate"),
    ("stella", "Stella"),
    ("ad_kit", "Kit"),
)


def asset_ok(name: str) -> bool:
    return (_DIR / name).is_file()


def _src(name: str) -> str:
    if asset_ok(f"{name}.webp"):
        return f"{ASSET}/{name}.webp"
    if asset_ok(f"{name}.png"):
        return f"{ASSET}/{name}.png"
    return ""


def _cast_html() -> str:
    bits = []
    for i, (key, name, role, step) in enumerate(CAST):
        src = _src(key)
        portrait = (
            f'<img src="{src}" alt="{html.escape(name)}"/>'
            if src
            else f'<span class="ph">{html.escape(name[0])}</span>'
        )
        bits.append(
            f'<div class="bird" data-id="{key}" data-step="{step}" style="animation-delay:{0.1 * i}s">'
            f"{portrait}<b>{html.escape(name)}</b><span>{html.escape(role)}</span></div>"
        )
    return "".join(bits)


def _path_html() -> str:
    return "".join(
        f'<div class="step" data-id="{html.escape(sid)}" data-label="{html.escape(label)}"></div>'
        for sid, label in PATH_STEPS
    )


def render_theater(
    *,
    url: str = "",
    name: str = "",
    geo: str = "",
    goal: str = "",
    assets: str = "",
    error: str = "",
    play: str = "",
    campaign: dict[str, Any] | None = None,
    campaign_id: str = "",
    key: str = "",
) -> str:
    hero = _src("hero")
    flo = _src("flo")
    hero_tag = f'<img class="mural" src="{hero}" alt="The flamingo flock roost"/>' if hero else ""
    err = f'<p class="err" id="err">{html.escape(error)}</p>' if error else '<p class="err" id="err"></p>'
    seed = {
        "name": DEMO_SHOP["name"],
        "geo": DEMO_SHOP["geo"],
        "goal": DEMO_SHOP["goal"],
        "url": DEMO_SHOP["url"],
        "kitPath": DEMO_SHOP["kitPath"],
        "campaignId": DEMO_SHOP["campaignId"],
        "landingPath": DEMO_SHOP.get("landingPath"),
        "utmPath": DEMO_SHOP.get("utmPath"),
        "markers": ["rLF34cfolz9TJA92F", "glensbakehouse.com", DEMO_SHOP["campaignId"]],
    }
    boot: dict[str, Any] = {"play": play, "seed": seed}
    if campaign and campaign_id:
        cfg = dict(campaign.get("engineConfig") or {})
        cfg.pop("price_inr", None)
        boot["campaign"] = {
            "id": campaign_id,
            "status": campaign.get("status"),
            "brief": campaign.get("brief") or {},
            "engineConfig": cfg,
            "kitPath": campaign.get("kitPath"),
            "landingPath": campaign.get("landingPath"),
            "studioPath": f"/s/{campaign_id}?k={key}" if key else "",
            "runPath": f"/r/{campaign_id}?k={key}" if key else "",
        }
    payload = json.dumps(boot).replace("<", "\\u003c")
    chip_img = f'<img src="{flo}" alt=""/>' if flo else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Leadsy Flock</title>
  <link rel="stylesheet" href="{ASSET}/theater.css?v=story"/>
</head>
<body data-stage="roost">
<div class="stage">
  <section class="roost" id="roost">{hero_tag}
    <div class="grain" aria-hidden="true"></div>
    <div class="veil"></div>
    <div class="cast">{_cast_html()}</div>
  </section>
  <div class="plate">
    <header class="mast">
      <a class="word" href="/">Leadsy Flock</a>
      <nav>
        <a href="/dash">observatory</a>
        <a href="/architecture">architecture</a>
        <a href="/blog">blog</a>
        <span class="here" id="status">roost</span>
      </nav>
    </header>
    <h1 class="headline" id="headline">The flock is already here.</h1>
    <p class="lede" id="lede">Leadsy Flock is a five-bird studio for neighbourhood shops. Paste a listing you own. Scout reads the truth of it, Inka paints from this shop's own photos, Stella hands you the kit. We never autopost.</p>
    <div class="story" aria-label="Who we are and what we unlock">
      <article class="beat" style="--d:.08s">
        <i class="glow" aria-hidden="true"></i>
        <b>Who</b>
        <span>Five birds. One roost. Built for India's SMBs.</span>
      </article>
      <article class="beat" style="--d:.16s">
        <i class="glow" aria-hidden="true"></i>
        <b>Listen</b>
        <span>Scout grounds the listing, maps, and the shop's own site.</span>
      </article>
      <article class="beat" style="--d:.24s">
        <i class="glow" aria-hidden="true"></i>
        <b>Paint</b>
        <span>Inka films the courtyard from this shop's photos — never fake UGC.</span>
      </article>
      <article class="beat" style="--d:.32s">
        <i class="glow" aria-hidden="true"></i>
        <b>Unlock</b>
        <span>A paste kit for Meta, WhatsApp, Google. Flo never posts it.</span>
      </article>
    </div>
    <div class="capsule">
      <input id="url" name="url" type="url" required placeholder="A website or Google listing"
        value="{html.escape(url)}" autocomplete="url" aria-label="Shop listing URL"/>
      <button type="button" id="hire">Hire the flock</button>
      <button type="button" class="yes" id="yes" hidden>YES</button>
    </div>
    {err}
    <a class="chip" id="seed-chip" href="/?play=seed">{chip_img}Glen's Bakehouse · seeded kit</a>
    <div class="quote" id="quote">
      <p class="quiet">The flock is ready</p>
      <p class="lede">Scout tracks. Inka paints. Stella hosts. Flo never autoposts.</p>
    </div>
    <div class="path" id="path" aria-hidden="true">{_path_html()}</div>
    <button type="button" class="linkish" id="more-toggle">or name the shop</button>
    <div class="more" id="more">
      <input id="name" name="name" type="text" placeholder="Shop name" value="{html.escape(name)}" aria-label="Shop name"/>
      <input id="geo" name="geo" type="text" placeholder="Area / city" value="{html.escape(geo)}" aria-label="Area or city"/>
      <input id="goal" name="goal" type="text" placeholder="What success looks like" value="{html.escape(goal)}" aria-label="Goal"/>
      <input id="assets" name="assets" type="text" placeholder="Extra photo or menu URLs" value="{html.escape(assets)}" aria-label="Asset URLs"/>
    </div>
    <p class="note">Paste a listing you own. The Glen's Bakehouse kit is the seeded demo — do not contact the bakery.</p>
  </div>
  <section class="delivery" id="delivery">
    <iframe id="kit-frame" title="Paste kit" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-downloads"></iframe>
  </section>
</div>
<script>window.__FLOCK__ = {payload};</script>
<script src="{ASSET}/theater.js?v=story"></script>
</body>
</html>
"""


def render_capture(**kwargs: Any) -> str:
    return render_theater(**kwargs)


def render_run(campaign_id: str, campaign: dict[str, Any], *, key: str) -> str:
    brief = campaign.get("brief") or {}
    return render_theater(
        campaign_id=campaign_id,
        campaign=campaign,
        key=key,
        url=str(brief.get("website") or brief.get("googleListing") or ""),
        name=str(brief.get("businessName") or ""),
        geo=str(brief.get("geo") or ""),
        goal=str(brief.get("goal") or ""),
    )

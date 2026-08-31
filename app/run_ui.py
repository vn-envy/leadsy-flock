# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Hackathon door: paste a URL, YES the quote, watch the kit land. No Telegram CTA."""

from __future__ import annotations

import html
import json
from typing import Any

_CSS = """
:root {
  --bg:#14181f; --fg:#f3eee6; --muted:#b7aea2; --accent:#c4a574; --accent-fg:#14181f;
  --surface:#1c222c; --line:#2c3340; --ember:#e08a4a; --slate:#7eaebe; --stamp:#b54a4a;
}
* { box-sizing:border-box; }
html, body { margin:0; min-height:100%; }
body {
  font-family: system-ui, "Segoe UI", sans-serif;
  background: var(--bg); color: var(--fg);
}
h1, h2, h3 { font-family: Georgia, "Iowan Old Style", "Times New Roman", serif; font-weight:500; }
a { color: var(--accent); }
.kicker {
  letter-spacing:.18em; font-size:.72rem; text-transform:uppercase;
  color: var(--accent); font-weight:650; margin:0 0 .6rem;
}
.wrap { width:min(72rem, calc(100% - 2rem)); margin:0 auto; padding:2rem 0 4rem; }
.nav { display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:0 0 1.4rem; }
.nav .word { color:var(--fg); text-decoration:none; font-family:Georgia,serif; font-size:1.15rem; }
.pill {
  display:inline-flex; align-items:center; justify-content:center; gap:.4rem;
  background:var(--accent); color:var(--accent-fg); border:0; border-radius:999px;
  padding:.75rem 1.2rem; font-weight:650; text-decoration:none; min-height:2.7rem; cursor:pointer;
  font-size:1rem;
}
.pill:disabled { opacity:.55; cursor:not-allowed; }
.pill.ghost { background:transparent; color:var(--accent); border:1px solid var(--line); }
.hero { display:grid; gap:2rem; align-items:start; }
@media (min-width:860px) { .hero { grid-template-columns:1.1fr .9fr; } }
.hero h1 { font-size:clamp(2rem,5vw,3.2rem); line-height:1.12; margin:0 0 .8rem; }
.lede { color:var(--muted); line-height:1.6; max-width:38rem; }
.panel, .card {
  background:var(--surface); border:1px solid var(--line); border-radius:1rem; padding:1rem 1.1rem;
}
label { display:block; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin:0.85rem 0 .35rem; }
input, textarea {
  width:100%; background:var(--bg); color:var(--fg); border:1px solid var(--line);
  border-radius:.7rem; padding:.7rem .8rem; font:inherit;
}
textarea { min-height:5.2rem; resize:vertical; }
.muted { color:var(--muted); font-size:.85rem; }
.err { color:#e08a4a; font-size:.9rem; margin:.4rem 0 0; }
.flock-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(6.2rem,1fr)); gap:.6rem; margin-top:1rem; }
.flock-card { background:var(--surface); border:1px solid var(--line); border-radius:1rem; padding:.55rem .4rem .7rem; text-align:center; }
.flock-card svg { width:4.6rem; height:5.5rem; margin:0 auto; display:block; }
.flock-card h3 { font-size:.9rem; margin:.25rem 0 .05rem; }
.flock-card p { margin:0; font-size:.68rem; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
.bird { overflow:visible; display:block; }
.bird .stroke { fill:none; stroke:var(--accent); stroke-width:1.6; stroke-linejoin:round; stroke-linecap:round; }
.bird .fill-bone { fill:var(--fg); }
.bird .fill-ink { fill:var(--surface); }
.bird .fill-gold { fill:var(--accent); }
@keyframes bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
@keyframes talk { 0%,70%,100%{transform:scaleY(1)} 78%{transform:scaleY(.55) translateY(2px)} }
@keyframes spin-slow { from{transform:rotate(0)} to{transform:rotate(360deg)} }
@keyframes drip { 0%{transform:translateY(0);opacity:1} 100%{transform:translateY(14px);opacity:0} }
@keyframes glow { 0%,100%{opacity:.45} 50%{opacity:1} }
@keyframes bead { 0%,100%{transform:translateX(0)} 50%{transform:translateX(3px)} }
.bird.flo .body { animation:bob 3.2s ease-in-out infinite; transform-origin:40px 80px; }
.bird.flo .beak { animation:talk 2.8s ease-in-out infinite; transform-origin:52px 34px; }
.bird.flo .ring { animation:spin-slow 12s linear infinite; transform-origin:54px 36px; }
.bird.bri .beads { animation:bead 1.6s ease-in-out infinite; }
.bird.bri .body { animation:bob 3.6s ease-in-out infinite; transform-origin:40px 80px; }
.bird.scout .scope { animation:spin-slow 8s linear infinite; transform-origin:50px 28px; }
.bird.scout .body { animation:bob 2.4s ease-in-out infinite; transform-origin:40px 80px; }
.bird.inka .drop { animation:drip 2.2s ease-in infinite; }
.bird.inka .body { animation:bob 3.8s ease-in-out infinite; transform-origin:40px 80px; }
.bird.stella .lantern { animation:glow 2.4s ease-in-out infinite; }
.bird.stella .body { animation:bob 3.1s ease-in-out infinite; transform-origin:40px 80px; }
.steps { display:flex; flex-wrap:wrap; gap:.4rem; margin:1rem 0; }
.step {
  border:1px solid var(--line); border-radius:999px; padding:.35rem .7rem;
  font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);
}
.step.on { border-color:var(--accent); color:var(--accent); }
.step.ok { border-color:#7eaebe; color:#7eaebe; }
.price { font-size:clamp(1.6rem,4vw,2.4rem); margin:.2rem 0; }
iframe.studio {
  width:100%; min-height:70vh; border:1px solid var(--line); border-radius:1rem;
  background:var(--bg); margin-top:1.2rem;
}
.quote { margin:1rem 0 1.2rem; }
"""

_BIRDS = {
    "flo": (
        '<svg class="bird flo" viewBox="0 0 80 100" aria-hidden="true"><g class="body">'
        '<ellipse cx="40" cy="64" rx="20" ry="24" class="fill-ink stroke"/>'
        '<circle cx="40" cy="32" r="15" class="fill-bone stroke"/>'
        '<circle cx="46" cy="31" r="2.4" fill="#14181f"/>'
        '<polygon class="beak fill-gold" points="52,34 64,36 52,40"/>'
        '<circle class="ring" cx="54" cy="36" r="9" fill="none" stroke="#c4a574" stroke-width="1.3" stroke-dasharray="3 5"/>'
        '<path d="M34 18 L40 8 L46 18" class="fill-gold stroke"/>'
        "</g></svg>"
    ),
    "bri": (
        '<svg class="bird bri" viewBox="0 0 80 100" aria-hidden="true"><g class="body">'
        '<rect x="26" y="48" width="28" height="32" rx="10" class="fill-ink stroke"/>'
        '<circle cx="40" cy="34" r="14" class="fill-bone stroke"/>'
        '<text x="40" y="68" text-anchor="middle" font-size="11" fill="#c4a574" font-family="Georgia,serif">₹</text>'
        '<g class="beads"><circle cx="22" cy="72" r="3" fill="#e08a4a"/><circle cx="18" cy="80" r="3" fill="#c4a574"/></g>'
        "</g></svg>"
    ),
    "scout": (
        '<svg class="bird scout" viewBox="0 0 80 100" aria-hidden="true"><g class="body">'
        '<ellipse cx="40" cy="66" rx="16" ry="22" class="fill-ink stroke"/>'
        '<circle cx="40" cy="30" r="13" class="fill-bone stroke"/>'
        '<g class="scope"><circle cx="50" cy="28" r="7" fill="none" stroke="#7eaebe" stroke-width="1.6"/></g>'
        "</g></svg>"
    ),
    "inka": (
        '<svg class="bird inka" viewBox="0 0 80 100" aria-hidden="true"><g class="body">'
        '<ellipse cx="40" cy="64" rx="19" ry="23" class="fill-ink stroke"/>'
        '<circle cx="40" cy="33" r="14" class="fill-bone stroke"/>'
        '<circle class="drop" cx="18" cy="44" r="2.4" fill="#14181f"/>'
        "</g></svg>"
    ),
    "stella": (
        '<svg class="bird stella" viewBox="0 0 80 100" aria-hidden="true"><g class="body">'
        '<ellipse cx="40" cy="66" rx="18" ry="22" class="fill-ink stroke"/>'
        '<circle cx="40" cy="34" r="14" class="fill-bone stroke"/>'
        '<g class="lantern"><rect x="34" y="6" width="12" height="10" rx="1" fill="#c4a574"/></g>'
        "</g></svg>"
    ),
}

_META = {
    "flo": ("Flo", "Director"),
    "bri": ("Bri", "Strategist"),
    "scout": ("Scout", "Tracker"),
    "inka": ("Inka", "Artist"),
    "stella": ("Stella", "Host"),
}


def _cards(ids: tuple[str, ...] = ("flo", "bri", "scout", "inka", "stella")) -> str:
    bits = []
    for i in ids:
        svg = _BIRDS.get(i) or ""
        name, role = _META.get(i, (i, ""))
        bits.append(
            f'<div class="flock-card">{svg}<h3>{html.escape(name)}</h3>'
            f'<p>{html.escape(role)}</p></div>'
        )
    return "".join(bits)


def render_capture(
    *,
    url: str = "",
    name: str = "",
    geo: str = "",
    goal: str = "",
    assets: str = "",
    error: str = "",
) -> str:
    err = f'<p class="err" role="alert">{html.escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Leadsy Flock · brief Flo</title>
  <style>{_CSS}</style>
</head>
<body>
<main class="wrap">
  <nav class="nav">
    <a class="word" href="/">Leadsy Flock</a>
    <a class="pill ghost" href="/demo">Clock a fictional stall</a>
  </nav>
  <section class="hero">
    <div>
      <p class="kicker">AI growth agency · India</p>
      <h1>Paste a shop URL. Hire the flock.</h1>
      <p class="lede">A website or Google listing is enough. Bri quotes rupees. You tap YES.
      Scout → Inka → Gate → Stella → Ad Kit land in a studio URL. We never autopost.</p>
      <p class="muted">Launch kit ₹5,997 · Scout + Inka + Stella · no retainers to start</p>
    </div>
    <form class="panel" id="brief" method="post" action="/" data-url-field>
      <p class="kicker">The brief</p>
      <label for="url">Website or Google listing URL</label>
      <input id="url" name="url" type="url" required placeholder="https://share.google/… or your site"
        value="{html.escape(url)}" autocomplete="url"/>
      <label for="name">Shop name <span class="muted">(optional)</span></label>
      <input id="name" name="name" type="text" placeholder="Mira's Chai" value="{html.escape(name)}"/>
      <label for="geo">Area / city <span class="muted">(optional)</span></label>
      <input id="geo" name="geo" type="text" placeholder="Koramangala, Bangalore" value="{html.escape(geo)}"/>
      <label for="goal">What success looks like <span class="muted">(optional)</span></label>
      <input id="goal" name="goal" type="text" placeholder="Evening takeaway cups from office workers" value="{html.escape(goal)}"/>
      <label for="assets">Extra photos, menu PDFs, listing links <span class="muted">(optional)</span></label>
      <textarea id="assets" name="assets" placeholder="https://… one per line">{html.escape(assets)}</textarea>
      {err}
      <p style="margin:1.1rem 0 0"><button class="pill" type="submit">Get a quote</button></p>
      <p class="muted" style="margin:.7rem 0 0">Paste a listing or site you own. Do not paste a shop you do not operate.</p>
    </form>
  </section>
  <p class="kicker" style="margin-top:2.2rem">The flock</p>
  <div class="flock-row">{_cards()}</div>
</main>
</body>
</html>
"""


def render_run(campaign_id: str, campaign: dict[str, Any], *, key: str) -> str:
    brief = campaign.get("brief") or {}
    rec = campaign.get("engineConfig") or {}
    hired = [str(x) for x in (rec.get("hired") or ["scout", "inka", "stella"])]
    price = rec.get("price_inr") or campaign.get("quotedInr") or 5997
    business = html.escape(str(brief.get("businessName") or "listing"))
    geo = html.escape(str(brief.get("geo") or ""))
    goal = html.escape(str(brief.get("goal") or ""))
    source = str(brief.get("website") or brief.get("googleListing") or "")
    source_h = html.escape(source)
    source_html = f'<a href="{source_h}">{source_h}</a>' if source.startswith("http") else ""
    hired_cards = _cards(tuple(h for h in ("scout", "inka", "stella") if h in hired) or ("scout", "inka", "stella"))
    bootstrap = {
        "id": campaign_id,
        "key": key,
        "status": campaign.get("status") or "planned",
        "hired": hired,
        "priceInr": price,
        "kitPath": campaign.get("kitPath"),
        "landingPath": campaign.get("landingPath"),
        "studioPath": f"/s/{campaign_id}?k={key}",
    }
    payload = json.dumps(bootstrap).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Run · {business}</title>
  <style>{_CSS}</style>
</head>
<body>
<main class="wrap">
  <nav class="nav">
    <a class="word" href="/">Leadsy Flock</a>
    <span class="muted" id="status-pill">{html.escape(str(campaign.get("status") or "planned"))}</span>
  </nav>
  <p class="kicker">{business}{f" · {geo}" if geo else ""}</p>
  <h1 id="headline">Bri's quote</h1>
  <p class="lede" id="lede">{goal or "Scout reads the listing. Inka makes the kit. Stella hosts the landing. You paste into Ads Manager."}</p>
  <p class="muted" id="source">{source_html}</p>
  <section class="panel quote" id="quote-panel">
    <p class="kicker">Hired</p>
    <div class="flock-row">{hired_cards}</div>
    <p class="price">₹{html.escape(str(price))}</p>
    <p class="muted">Scout ₹1,999 + Inka ₹2,499 + Stella ₹1,499. Flo, Bri, and Ledge are free. We never autopost.</p>
    <p style="margin:1rem 0 0"><button class="pill" id="yes" type="button">YES</button></p>
  </section>
  <section id="tracker" hidden>
    <p class="kicker">The flock at work</p>
    <div class="steps" id="steps"></div>
    <p class="muted" id="track-note">YES starts Scout. Films fill in on this same URL when Veo finishes.</p>
  </section>
  <iframe class="studio" id="studio" title="Owner studio" hidden sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
</main>
<script>
const boot = {payload};
const STEPS = [
  {{id:"scout", label:"Scout"}},
  {{id:"inka", label:"Inka"}},
  {{id:"inka_harvest", label:"Harvest"}},
  {{id:"creative_gate", label:"Gate"}},
  {{id:"stella", label:"Stella"}},
  {{id:"ad_kit", label:"Ad Kit"}},
];
const yesBtn = document.getElementById("yes");
const quotePanel = document.getElementById("quote-panel");
const tracker = document.getElementById("tracker");
const stepsEl = document.getElementById("steps");
const studio = document.getElementById("studio");
const statusPill = document.getElementById("status-pill");
const headline = document.getElementById("headline");
const lede = document.getElementById("lede");
let timer = null;

function paintSteps(receipts, status) {{
  const done = new Set((receipts || []).filter(r => r.status === "ok").map(r => r.step));
  const current = (receipts || []).filter(r => r.status === "running").map(r => r.step)[0]
    || (status === "running" ? STEPS.find(s => !done.has(s.id))?.id : "");
  stepsEl.innerHTML = STEPS.map(s => {{
    let cls = "step";
    if (done.has(s.id)) cls += " ok";
    else if (s.id === current) cls += " on";
    return `<span class="${{cls}}">${{s.label}}</span>`;
  }}).join("");
}}

function showStudio() {{
  headline.textContent = "Delivery room";
  lede.textContent = "This page is the delivery room. Paste into your own Ads Manager. We do not autopost.";
  quotePanel.hidden = true;
  tracker.hidden = false;
  studio.hidden = false;
  studio.src = boot.studioPath;
}}

async function tick() {{
  try {{
    const [cRes, mRes] = await Promise.all([
      fetch("/v1/campaigns/" + boot.id),
      fetch("/media/" + boot.id + "/ready"),
    ]);
    if (!cRes.ok) return;
    const c = await cRes.json();
    const ready = mRes.ok ? await mRes.json() : {{}};
    statusPill.textContent = c.status || "";
    paintSteps(c.receipts || [], c.status);
    const films = ["still","clip","clip-feed","jingle"].filter(s => ready[s]).length;
    const note = document.getElementById("track-note");
    if (note) note.textContent = films
      ? films + " media slot" + (films===1?"":"s") + " ready. Films keep filling in."
      : "YES starts Scout. Films fill in on this same URL when Veo finishes.";
    if (c.status === "completed" || c.kitPath) showStudio();
  }} catch (err) {{ /* keep polling */ }}
}}

function startPoll() {{
  tracker.hidden = false;
  if (timer) return;
  tick();
  timer = setInterval(tick, 2500);
}}

yesBtn.addEventListener("click", async () => {{
  yesBtn.disabled = true;
  yesBtn.textContent = "Hiring…";
  try {{
    const res = await fetch("/v1/campaigns/" + boot.id + "/approve", {{method:"POST"}});
    if (!res.ok) {{
      yesBtn.disabled = false;
      yesBtn.textContent = "YES";
      return;
    }}
    yesBtn.textContent = "Hired";
    quotePanel.querySelector(".muted").textContent = "Scout is reading the listing. Stay on this page.";
    startPoll();
  }} catch (err) {{
    yesBtn.disabled = false;
    yesBtn.textContent = "YES";
  }}
}});

if (boot.status === "completed" || boot.kitPath) {{
  showStudio();
  startPoll();
}} else if (boot.status === "running") {{
  yesBtn.disabled = true;
  yesBtn.textContent = "Hired";
  startPoll();
}}
</script>
</body>
</html>
"""

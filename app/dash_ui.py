# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public observatory page — charts, seed burn, Cloud Run proof. No tables."""

from __future__ import annotations

import html
import json
from typing import Any

from app.observe import snapshot
from app.run_ui import ASSET, _cast_html, _src


def render_html(data: dict[str, Any] | None = None) -> str:
    boot = data or snapshot(live=False)
    payload = json.dumps(boot).replace("<", "\\u003c")
    hero = _src("hero")
    run = boot.get("run") or {}
    rev = html.escape(str(run.get("revision") or "local"))
    service = html.escape(str(run.get("service") or "flock-api"))
    region = html.escape(str(run.get("region") or ""))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Observatory · Leadsy Flock</title>
  <link rel="stylesheet" href="{ASSET}/dash.css?v=open"/>
</head>
<body>
<section class="wash" style="background-image:url('{hero}')">
  <div class="grain" aria-hidden="true"></div>
  <div class="veil"></div>
  <div class="cast">{_cast_html()}</div>
</section>
<main class="sheet">
  <header class="mast">
    <a class="word" href="/">Leadsy Flock</a>
    <nav>
      <a href="/">roost</a>
      <a href="/demo">seeded kit</a>
      <a href="/architecture">architecture</a>
      <a href="/blog">blog</a>
      <span class="here">observatory</span>
    </nav>
  </header>
  <p class="quiet">Cloud Run · {service} · {region}</p>
  <h1>The flock, in the open.</h1>
  <p class="lede">Revision <code id="revision">{rev}</code> is serving. The Glen's Bakehouse seed shows the tokens, tools, and Vertex list-price burn that made the kit — not a spreadsheet, not an invoice. We do not autopost.</p>
  <div class="stats" id="stats"></div>
  <div class="grid">
    <section class="card span-2" id="seed-card">
      <p class="quiet">Seed · Glen's Bakehouse</p>
      <p class="seed-lede" id="seed-lede">Vertex list-price reconstruction from receipts. Not a Google invoice. Not a sell price.</p>
      <div class="stats seed-stats" id="seed-stats"></div>
      <div class="mix-row seed-mix">
        <div class="donut" id="seed-donut" aria-hidden="true"></div>
        <div class="stack" id="seed-kinds"></div>
      </div>
      <p class="quiet">Tools this run</p>
      <div class="chips" id="seed-tools"></div>
      <p class="quiet">Models</p>
      <div class="chips" id="seed-models"></div>
    </section>
    <section class="card span-2">
      <p class="quiet">Engine path</p>
      <div class="legend">
        <span><i class="ok"></i> ok</span>
        <span><i class="run"></i> running</span>
        <span><i class="other"></i> other</span>
      </div>
      <div class="vbars" id="engines"></div>
    </section>
    <section class="card">
      <p class="quiet">Cloud Run proof</p>
      <div id="proof"></div>
    </section>
    <section class="card">
      <p class="quiet">Campaign mix</p>
      <div class="mix-row">
        <div class="donut" id="donut" aria-hidden="true"></div>
        <div class="stack" id="status"></div>
      </div>
    </section>
    <section class="card">
      <p class="quiet">Latency · 1h</p>
      <div class="stack" id="latency"></div>
    </section>
    <section class="card span-2">
      <p class="quiet">Landing hits</p>
      <div class="stack" id="hits"></div>
    </section>
  </div>
  <p class="note">{html.escape(str(boot.get("note") or ""))}</p>
</main>
<script>window.__DASH__ = {payload};</script>
<script src="{ASSET}/dash.js?v=open"></script>
</body>
</html>
"""

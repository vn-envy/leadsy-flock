# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public architecture page — the judge diagram, same chrome as the roost."""

from __future__ import annotations

import html

from app.run_ui import ASSET, _cast_html, _src

PNG = f"{ASSET}/architecture.png"


def render_html() -> str:
    hero = _src("hero")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Architecture · Leadsy Flock</title>
  <link rel="stylesheet" href="{ASSET}/dash.css?v=arch"/>
  <style>
    .arch {{
      margin: .4rem 0 1rem;
      border-radius: 1.1rem;
      border: 1px solid var(--line);
      background: var(--paper);
      overflow: hidden;
    }}
    .arch img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .criteria {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: .55rem;
      margin: 0 0 1rem;
    }}
    .criteria article {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 1rem;
      padding: .75rem .85rem .9rem;
    }}
    .criteria b {{
      display: block;
      font-size: .62rem;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: var(--ash);
      margin-bottom: .3rem;
    }}
    .criteria span {{
      display: block;
      font-size: .84rem;
      line-height: 1.4;
      color: var(--ink);
    }}
    @media (max-width: 800px) {{
      .criteria {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
<section class="wash" style="background-image:url('{hero}')">
  <div class="grain" aria-hidden="true"></div>
  <div class="veil"></div>
  <div class="cast">{_cast_html()}</div>
</section>
<main class="sheet">
  <header class="mast">
    <a class="word" href="/demo">Leadsy Flock</a>
    <nav>
      <a href="/demo">roost</a>
      <a href="/dash">observatory</a>
      <a href="/blog">blog</a>
      <span class="here">architecture</span>
    </nav>
  </header>
  <p class="quiet">Fortified Enterprise Fleet · asia-south1</p>
  <h1>How the flock is built.</h1>
  <p class="lede">One path from a listing the shop owns to a paste kit. Gemini 3.5 and Google ADK on Cloud Run. Pub/Sub fans the birds. Vertex models paint. Receipts, memory, and traces stay on the record. The flock never autoposts.</p>
  <div class="criteria" aria-label="Judging stack">
    <article><b>Mandatory</b><span>Gemini 3.5 Flash via Vertex. Google ADK. Cloud Run flock-api and flock-worker.</span></article>
    <article><b>Fleet</b><span>A2A AgentCard. Model Armor. Memory Bank. Cloud Trace. Firestore receipts.</span></article>
    <article><b>Bonus models</b><span>Veo 3.1, Gemma 3, Gemini Image, TTS, Lyria, Search + Maps.</span></article>
    <article><b>Human yes</b><span>YES starts the pipeline. Owner pastes the kit. Observatory shows tokens, tools, list-price burn.</span></article>
  </div>
  <figure class="arch">
    <img src="{PNG}" alt="{html.escape("Leadsy Flock end-to-end architecture: shop listing, Cloud Run door, Pub/Sub worker, Vertex models, record, delivery")}"/>
  </figure>
  <p class="note">Drawn with <a href="https://github.com/mingrammer/diagrams">mingrammer/diagrams</a>. Source: <code>scripts/gen_architecture.py</code>. Not a Google invoice. We do not autopost.</p>
</main>
</body>
</html>
"""

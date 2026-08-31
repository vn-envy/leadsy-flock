# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public backend path — Firestore receipts + Cloud Trace console links."""

from __future__ import annotations

import html
import json

from app.observe import snapshot
from app.run_ui import ASSET, _cast_html, _src


def render_html() -> str:
    boot = snapshot(live=False)
    path = boot.get("path") or {}
    run = boot.get("run") or {}
    payload = json.dumps({"path": path, "run": run}).replace("<", "\\u003c")
    hero = _src("hero")
    name = html.escape(str(path.get("name") or "Glen's Bakehouse"))
    cid = html.escape(str(path.get("campaignId") or ""))
    hops = path.get("hops") or []
    console = path.get("console") or run.get("console") or {}
    hop_html = "".join(_hop(h) for h in hops) or "<p class='quiet'>Receipts not loaded yet.</p>"
    links = _console(console)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Backend path · Leadsy Flock</title>
  <link rel="stylesheet" href="{ASSET}/dash.css?v=trace"/>
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
      <a href="/architecture">architecture</a>
      <a href="/blog">blog</a>
      <span class="here">trace</span>
    </nav>
  </header>
  <p class="quiet">What ran · {cid}</p>
  <h1>The backend path, on the record.</h1>
  <p class="lede">{name} is the seeded kit. Every hop below is a Firestore receipt. Worker spans are named <code>engine.&lt;step&gt;</code> on Cloud Run <code>flock-worker</code>. Console links need a Google account on this GCP project. We do not autopost. Do not contact the bakery.</p>
  <div class="card span-2">
    <p class="quiet">Cloud Run traces</p>
    {links}
    <p class="seed-lede">In Cloud Trace Explorer search <code>engine.scout</code> (then inka, inka_harvest, creative_gate, stella, ad_kit). Attribute <code>campaign.id</code> = <code>{cid}</code>.</p>
  </div>
  <ol class="hops" id="hops">{hop_html}</ol>
  <p class="note">{html.escape(str(path.get("note") or ""))} JSON: <a href="/v1/trace">/v1/trace</a>.</p>
</main>
<script>window.__TRACE__ = {payload};</script>
</body>
</html>
"""


def _console(console: dict) -> str:
    if not console:
        return "<p class='quiet'>Console links appear when GOOGLE_CLOUD_PROJECT is set.</p>"
    items = (
        ("Worker traces (the engines)", console.get("workerTraces")),
        ("API traces (the door)", console.get("apiTraces")),
        ("Cloud Trace explorer", console.get("traceExplorer")),
        ("Worker logs", console.get("workerLogs")),
    )
    bits = []
    for label, href in items:
        if not href:
            continue
        bits.append(
            f'<a class="chip" href="{html.escape(href)}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(label)}</a>"
        )
    return f'<div class="chips">{"".join(bits)}</div>' if bits else "<p class='quiet'>No console URLs.</p>"


def _hop(h: dict) -> str:
    step = html.escape(str(h.get("step") or ""))
    status = html.escape(str(h.get("status") or ""))
    service = html.escape(str(h.get("service") or ""))
    span = html.escape(str(h.get("span") or ""))
    say = html.escape(str(h.get("say") or ""))
    model = html.escape(str(h.get("model") or "—"))
    n = html.escape(str(h.get("n") or ""))
    when = html.escape(str(h.get("finishedAt") or h.get("startedAt") or "")[:19].replace("T", " "))
    tid = str(h.get("traceId") or "")
    trace_bit = ""
    if tid:
        trace_bit = f'<p class="quiet">trace <code>{html.escape(tid)}</code></p>'
    return (
        f'<li class="hop" data-status="{status}">'
        f'<p class="quiet">{n} · {service} · {status}</p>'
        f"<h2>{step}</h2>"
        f'<p class="lede">{say}</p>'
        f"<p><code>{span}</code> · {model}</p>"
        f'<p class="quiet">{when}</p>'
        f"{trace_bit}"
        f"</li>"
    )

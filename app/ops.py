# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Founder observability. OPS_TOKEN required. Not a customer surface."""

from __future__ import annotations

import hmac
import html
import os
from typing import Any

from app import ledger
from app.cost import estimate_campaign
from app.telegram_adapter import configured as telegram_configured


def ops_token() -> str:
    return (os.environ.get("OPS_TOKEN") or "").strip()


def configured() -> bool:
    return bool(ops_token())


def verify_token(provided: str | None) -> bool:
    expected = ops_token()
    if not expected:
        return False
    return hmac.compare_digest(expected, provided or "")


def extract_token(header: str | None, bearer: str | None, query: str | None) -> str | None:
    if header:
        return header.strip()
    if bearer and bearer.lower().startswith("bearer "):
        return bearer[7:].strip()
    if query:
        return query.strip()
    return None


def dashboard() -> dict[str, Any]:
    campaigns = ledger.list_campaigns(limit=40)
    if not isinstance(campaigns, list):
        campaigns = []
    rows = []
    for c in campaigns:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        if not cid:
            continue
        receipts = ledger.list_receipts(cid)
        est = estimate_campaign(cid, receipts if isinstance(receipts, list) else [])
        hits = ledger.list_events(cid, kind="landing_hit") if hasattr(ledger, "list_events") else []
        hit_n = len(hits) if isinstance(hits, list) else 0
        rec_steps = []
        if isinstance(receipts, list):
            rec_steps = [f"{r.get('step')}:{r.get('status')}" for r in receipts if isinstance(r, dict)]
        rows.append(
            {
                "id": cid,
                "name": (c.get("brief") or {}).get("businessName") or cid,
                "status": c.get("status"),
                "quotedInr": est.get("quotedInr"),
                "estimatedUsd": est.get("estimatedUsd"),
                "estimatedInr": est.get("estimatedInr"),
                "marginInr": est.get("marginInr"),
                "telegram": bool(c.get("telegramChatId")),
                "studioKey": bool(c.get("studioKey")),
                "kitPath": c.get("kitPath"),
                "landingPath": c.get("landingPath"),
                "hits": hit_n,
                "receipts": rec_steps,
                "updatedAt": c.get("updatedAt"),
            }
        )
    return {
        "telegramConfigured": telegram_configured(),
        "campaigns": rows,
        "note": "List-price reconstruction. Veo dominates. Not a Google invoice.",
    }


def render_html() -> str:
    data = dashboard()
    rows = []
    for c in data["campaigns"]:
        name = html.escape(str(c.get("name") or ""))
        cid = html.escape(str(c.get("id") or ""))
        kit = html.escape(str(c.get("kitPath") or ""))
        land = html.escape(str(c.get("landingPath") or ""))
        rec = html.escape(" → ".join(c.get("receipts") or [])[:180])
        tg = "tg" if c.get("telegram") else ""
        rows.append(
            f"<tr>"
            f"<td>{name}<div class='muted'>{cid}</div></td>"
            f"<td class='pill'>{html.escape(str(c.get('status') or ''))} {tg}</td>"
            f"<td>₹{c.get('quotedInr') or '—'}</td>"
            f"<td>${c.get('estimatedUsd')} · ₹{c.get('estimatedInr')}</td>"
            f"<td>₹{c.get('marginInr') if c.get('marginInr') is not None else '—'}</td>"
            f"<td>{c.get('hits') or 0}</td>"
            f"<td>{('<a href=' + kit + '>kit</a> ') if kit else ''}{('<a href=' + land + '>land</a>') if land else ''}</td>"
            f"</tr><tr><td colspan='7' class='muted'>{rec}</td></tr>"
        )
    body = "".join(rows) or "<tr><td class='muted' colspan='7'>No campaigns.</td></tr>"
    tg = "on" if data["telegramConfigured"] else "token not set"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Ops · Leadsy Flock</title>
  <style>
    body {{ margin:0; background:#14181f; color:#f3eee6; font-family:system-ui,sans-serif; }}
    main {{ width:min(1100px, calc(100% - 2rem)); margin:0 auto; padding:2.5rem 0 4rem; }}
    h1 {{ font-family:Georgia,serif; font-weight:560; }}
    .kicker {{ letter-spacing:.2em; font-size:12px; color:#c4a574; font-weight:600; }}
    a {{ color:#c4a574; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ text-align:left; padding:.55rem .35rem; border-bottom:1px solid #2c3340; font-size:14px; vertical-align:top; }}
    .muted {{ color:#b7aea2; font-size:12px; }}
    .pill {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#c4a574; }}
  </style>
</head>
<body>
<main>
  <p class="kicker">FOUNDER · OPS</p>
  <h1>Quoted vs burn</h1>
  <p class="muted">Telegram {html.escape(tg)}. {html.escape(str(data.get("note") or ""))}
  Public receipts stay on <a href="/console">/console</a>. This page is token-gated.</p>
  <table>
    <thead><tr><th>Campaign</th><th>Status</th><th>Quoted</th><th>Est. COGS</th><th>Spread</th><th>UTM</th><th></th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</main>
</body>
</html>
"""

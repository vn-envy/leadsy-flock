# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""HTTP surface for Mission Control, judges, landings, and Pub/Sub push."""

from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app import ledger, media
from app.armor import ArmorBlocked
from app.campaigns import (
    approve_campaign,
    campaign_view,
    create_campaign,
    decode_pubsub_push,
    list_campaign_summaries,
    record_consent,
    screen_text,
)
from app.settings import load_settings
from app.telegram_adapter import configured as telegram_configured
from app.telegram_adapter import handle_update
from app.worker import handle_step


def attach_flock_routes(app: FastAPI) -> None:
    @app.get("/v1/infra")
    def infra() -> dict:
        s = load_settings()
        return {
            "project": s.project_id,
            "region": s.region,
            "firestore": s.firestore_database,
            "topics": {
                "campaignSteps": s.campaign_topic_path,
                "dlq": f"projects/{s.project_id}/topics/{s.dlq_topic}",
                "alerts": f"projects/{s.project_id}/topics/{s.alerts_topic}",
            },
            "buckets": {"media": s.media_bucket, "logs": s.logs_bucket},
            "modelArmor": f"projects/{s.project_id}/locations/{s.armor_location}/templates/{s.armor_template}",
            "memoryBankId": s.memory_bank_id or None,
            "telegram": telegram_configured(),
        }

    @app.post("/v1/screen")
    def screen(body: dict) -> dict:
        text = (body or {}).get("text") or ""
        if not text:
            raise HTTPException(400, "text required")
        return screen_text(text)

    @app.post("/v1/campaigns")
    def create(body: dict) -> dict:
        brief = (body or {}).get("brief") or body or {}
        raw = (body or {}).get("rawText") or brief.get("rawText") or ""
        try:
            return create_campaign(brief, raw_text=raw)
        except ArmorBlocked as exc:
            raise HTTPException(status_code=403, detail={"error": "blocked", "verdict": exc.verdict}) from exc

    @app.get("/v1/campaigns")
    def list_all() -> dict:
        return {"campaigns": list_campaign_summaries()}

    @app.get("/v1/campaigns/{campaign_id}")
    def get_one(campaign_id: str) -> dict:
        view = campaign_view(campaign_id)
        if not view:
            raise HTTPException(404, "campaign not found")
        view.pop("landingHtml", None)
        return view

    @app.post("/v1/campaigns/{campaign_id}/approve")
    def approve(campaign_id: str) -> dict:
        try:
            return approve_campaign(campaign_id)
        except KeyError:
            raise HTTPException(404, "campaign not found") from None

    @app.get("/l/{campaign_id}", response_class=HTMLResponse)
    def landing(campaign_id: str) -> HTMLResponse:
        campaign = ledger.get_campaign(campaign_id)
        if not campaign or not campaign.get("landingHtml"):
            raise HTTPException(404, "landing not published")
        return HTMLResponse(campaign["landingHtml"])

    @app.get("/media/{campaign_id}/still")
    def campaign_still(campaign_id: str) -> Response:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        found = media.get_campaign_still(campaign_id)
        if not found:
            raise HTTPException(404, "still not published")
        data, mime = found
        return Response(
            content=data,
            media_type=mime or "image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/media/{campaign_id}/ready")
    def media_ready(campaign_id: str) -> dict:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        return {
            "still": media.campaign_asset_exists(campaign_id, media.STILL_NAMES),
            "clip": media.campaign_asset_exists(campaign_id, media.CLIP_NAMES),
            "jingle": media.campaign_asset_exists(campaign_id, media.JINGLE_NAMES),
        }

    @app.api_route("/media/{campaign_id}/clip", methods=["GET", "HEAD"])
    def campaign_clip(campaign_id: str, request: Request) -> Response:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        if request.method == "HEAD":
            if not media.campaign_asset_exists(campaign_id, media.CLIP_NAMES):
                raise HTTPException(404, "clip not harvested")
            return Response(status_code=200, media_type="video/mp4")
        found = media.get_campaign_clip(campaign_id)
        if not found:
            raise HTTPException(404, "clip not harvested")
        data, mime = found
        return Response(
            content=data,
            media_type=mime or "video/mp4",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.api_route("/media/{campaign_id}/jingle", methods=["GET", "HEAD"])
    def campaign_jingle(campaign_id: str, request: Request) -> Response:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        if request.method == "HEAD":
            if not media.campaign_asset_exists(campaign_id, media.JINGLE_NAMES):
                raise HTTPException(404, "jingle not harvested")
            return Response(status_code=200, media_type="audio/wav")
        found = media.get_campaign_jingle(campaign_id)
        if not found:
            raise HTTPException(404, "jingle not harvested")
        data, mime = found
        return Response(
            content=data,
            media_type=mime or "audio/wav",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.post("/v1/consents")
    def consents(body: dict) -> dict:
        campaign_id = (body or {}).get("campaignId") or ""
        name = ((body or {}).get("name") or "").strip()
        contact = ((body or {}).get("contact") or "").strip()
        if not campaign_id or not name or not contact:
            raise HTTPException(400, "campaignId, name, contact required")
        if not (body or {}).get("consent"):
            raise HTTPException(400, "consent checkbox required")
        try:
            return record_consent(
                campaign_id,
                name=name,
                contact=contact,
                source=str((body or {}).get("source") or "landing"),
            )
        except ArmorBlocked as exc:
            raise HTTPException(status_code=403, detail={"error": "blocked", "verdict": exc.verdict}) from exc
        except KeyError:
            raise HTTPException(404, "campaign not found") from None

    @app.get("/console", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        return HTMLResponse(_CONSOLE_HTML)

    @app.post("/v1/telegram/webhook")
    async def telegram(request: Request) -> dict:
        if not telegram_configured():
            raise HTTPException(501, "TELEGRAM_BOT_TOKEN not set")
        body = await request.json()
        return handle_update(body)

    @app.post("/internal/pubsub/campaign-steps")
    async def pubsub_push(request: Request) -> dict:
        if load_settings().service_name not in {"flock-worker", "local"}:
            raise HTTPException(404, "not a worker")
        body = await request.json()
        try:
            message = decode_pubsub_push(body)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(400, f"bad pubsub envelope: {exc}") from exc
        try:
            return handle_step(message)
        except Exception as exc:  # noqa: BLE001 — nack by returning 500 so Pub/Sub retries
            raise HTTPException(500, f"step failed: {exc}") from exc


def _safe_campaign_id(campaign_id: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9-]{3,80}", campaign_id or ""))


_CONSOLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Mission Control · Leadsy Flock</title>
  <style>
    body { margin:0; background:#0f1419; color:#f4efe6; font-family: system-ui, sans-serif; }
    main { width: min(960px, calc(100% - 2rem)); margin: 0 auto; padding: 2.5rem 0 4rem; }
    h1 { font-weight: 560; }
    .kicker { letter-spacing: .2em; font-size: 12px; color:#c4a574; }
    a { color:#c4a574; }
    table { width:100%; border-collapse: collapse; }
    th, td { text-align:left; padding: .7rem .4rem; border-bottom: 1px solid #2a333d; font-size: 14px; }
    .muted { color:#8b8378; }
    .pill { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#c4a574; }
  </style>
</head>
<body>
<main>
  <p class="kicker">LEADSY FLOCK · MISSION CONTROL</p>
  <h1>Receipts</h1>
  <p class="muted">Live from Firestore via flock-api. Open a campaign to watch Scout → Inka → Gate → Stella.</p>
  <table>
    <thead><tr><th>Campaign</th><th>Status</th><th>Updated</th><th></th></tr></thead>
    <tbody id="rows"><tr><td class="muted" colspan="4">Loading…</td></tr></tbody>
  </table>
  <pre id="detail" class="muted"></pre>
</main>
<script>
async function load() {
  const res = await fetch("/v1/campaigns");
  const body = await res.json();
  const rows = document.getElementById("rows");
  const list = body.campaigns || [];
  if (!list.length) { rows.innerHTML = "<tr><td class='muted' colspan='4'>No campaigns yet.</td></tr>"; return; }
  rows.innerHTML = list.map(c => {
    const name = (c.brief && c.brief.businessName) || c.id;
    const land = c.landingPath ? `<a href="${c.landingPath}">landing</a>` : "";
    return `<tr>
      <td><a href="#" data-id="${c.id}">${name}</a><div class="muted">${c.id}</div></td>
      <td class="pill">${c.status || ""}</td>
      <td class="muted">${(c.updatedAt || "").slice(0,19)}</td>
      <td>${land}</td>
    </tr>`;
  }).join("");
  rows.querySelectorAll("a[data-id]").forEach(a => a.onclick = (e) => { e.preventDefault(); show(a.dataset.id); });
}
async function show(id) {
  const res = await fetch("/v1/campaigns/" + id);
  const c = await res.json();
  const recs = (c.receipts || []).map(r => {
    const p = r.payload || {};
    return {
      step: r.step,
      status: r.status,
      verdict: p.verdict,
      draftRejected: p.draft && p.draft.rejected,
      grounding: (p.groundingUris || []).slice(0, 4),
      still: p.still,
      landing: p.url || p.landing,
      autopost: p.autopost,
    };
  });
  const rec = recs.map(r => r.step + ":" + r.status).join(" → ");
  document.getElementById("detail").textContent = rec + "\\n\\n" + JSON.stringify({
    status: c.status, landingPath: c.landingPath, receipts: recs, hired: (c.engineConfig || {}).hired
  }, null, 2);
}
load();
</script>
</body>
</html>
"""

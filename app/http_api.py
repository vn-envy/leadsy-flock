# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""HTTP surface for Mission Control, judges, landings, and Pub/Sub push."""

from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app import ledger, media
from app.armor import ArmorBlocked
from app.campaigns import (
    approve_campaign,
    campaign_view,
    create_campaign,
    decode_pubsub_push,
    list_campaign_summaries,
    record_consent,
    record_landing_hit,
    screen_text,
)
from app.demo import render_html as render_demo
from app.derive import download_name
from app.ops import configured as ops_configured
from app.ops import extract_token as ops_extract_token
from app.ops import render_html as render_ops
from app.ops import verify_token as ops_verify_token
from app.run_ui import render_capture, render_run
from app.settings import load_settings
from app.studio import check_key as studio_check_key
from app.studio import render_html as render_studio
from app.telegram_adapter import configured as telegram_configured
from app.telegram_adapter import handle_update
from app.telegram_adapter import verify_webhook_secret
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
            "ops": ops_configured(),
            "surfaces": {
                "home": "/",
                "run": "/r/{id}?k=",
                "demo": "/demo",
                "seedKit": "/k/google-listing-eaf57cae",
                "seedLanding": "/l/google-listing-eaf57cae",
                "ops": "/ops",
                "studio": "/s/{id}?k=",
            },
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
        view.pop("kitHtml", None)
        return view

    @app.post("/v1/campaigns/{campaign_id}/approve")
    def approve(campaign_id: str) -> dict:
        try:
            return approve_campaign(campaign_id)
        except KeyError:
            raise HTTPException(404, "campaign not found") from None

    @app.get("/l/{campaign_id}", response_class=HTMLResponse)
    def landing(campaign_id: str, request: Request) -> HTMLResponse:
        campaign = ledger.get_campaign(campaign_id)
        if not campaign or not campaign.get("landingHtml"):
            raise HTTPException(404, "landing not published")
        utm = {k: str(v) for k, v in request.query_params.items() if k.startswith("utm_")}
        if utm:
            record_landing_hit(campaign_id, utm, path=str(request.url.path))
        return HTMLResponse(campaign["landingHtml"])

    @app.get("/s/{campaign_id}", response_class=HTMLResponse)
    def studio(campaign_id: str, request: Request) -> HTMLResponse:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        campaign = ledger.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(404, "campaign not found")
        key = request.query_params.get("k")
        if not studio_check_key(campaign, key):
            raise HTTPException(403, "studio key required")
        return HTMLResponse(render_studio(campaign_id, campaign))

    @app.get("/ops", response_class=HTMLResponse)
    def ops(request: Request) -> HTMLResponse:
        if not ops_configured():
            raise HTTPException(501, "OPS_TOKEN not set")
        token = ops_extract_token(
            request.headers.get("x-ops-token"),
            request.headers.get("authorization"),
            request.query_params.get("token"),
        )
        if not ops_verify_token(token):
            raise HTTPException(403, "bad ops token")
        return HTMLResponse(render_ops())

    @app.get("/demo", response_class=HTMLResponse)
    def demo() -> HTMLResponse:
        return HTMLResponse(render_demo())

    @app.get("/k/{campaign_id}", response_class=HTMLResponse)
    def kit(campaign_id: str) -> HTMLResponse:
        campaign = ledger.get_campaign(campaign_id)
        if not campaign or not campaign.get("kitHtml"):
            raise HTTPException(404, "kit not published")
        return HTMLResponse(campaign["kitHtml"])

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
            slot: media.campaign_asset_exists(campaign_id, names)
            for slot, names in media.MEDIA_SLOTS.items()
        }

    @app.api_route("/media/{campaign_id}/{slot}", methods=["GET", "HEAD"])
    def campaign_media_slot(campaign_id: str, slot: str, request: Request) -> Response:
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        if slot not in media.MEDIA_SLOTS:
            raise HTTPException(404, "unknown slot")
        names = media.MEDIA_SLOTS[slot]
        if request.method == "HEAD":
            if not media.campaign_asset_exists(campaign_id, names):
                raise HTTPException(404, "asset not published")
            mime = "video/mp4" if slot.startswith("clip") else "audio/wav" if slot == "jingle" else "image/png"
            return Response(status_code=200, media_type=mime)
        found = media.get_campaign_slot(campaign_id, slot)
        if not found:
            raise HTTPException(404, "asset not published")
        data, mime = found
        if slot.startswith("clip"):
            mime = mime or "video/mp4"
        elif slot == "jingle":
            mime = mime or "audio/wav"
        else:
            mime = mime or "image/png"
        return Response(
            content=data,
            media_type=mime,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="{download_name(campaign_id, slot)}"',
            },
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
        if not verify_webhook_secret(request.headers.get("X-Telegram-Bot-Api-Secret-Token")):
            raise HTTPException(403, "bad telegram secret")
        body = await request.json()
        runner = getattr(request.app.state, "runner", None)
        return await handle_update(body, runner=runner)

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

    @app.get("/", response_class=HTMLResponse, name="capture_home")
    def capture_home(request: Request) -> HTMLResponse:
        q = request.query_params
        return HTMLResponse(
            render_capture(
                url=q.get("url") or "",
                name=q.get("name") or "",
                geo=q.get("geo") or "",
                goal=q.get("goal") or "",
                assets=q.get("assets") or "",
            )
        )

    @app.post("/", name="capture_submit")
    async def capture_submit(request: Request):
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            body = await request.json()
            brief = dict((body or {}).get("brief") or body or {})
            raw = str((body or {}).get("rawText") or "")
        else:
            form = await request.form()
            brief = {
                "url": str(form.get("url") or ""),
                "businessName": str(form.get("name") or form.get("businessName") or ""),
                "geo": str(form.get("geo") or ""),
                "goal": str(form.get("goal") or ""),
                "assetUris": str(form.get("assets") or form.get("assetUris") or ""),
            }
            raw = " ".join(
                p for p in (brief["businessName"], brief["geo"], brief["goal"]) if p
            )
        url = str(brief.get("url") or brief.get("website") or brief.get("googleListing") or "").strip()
        if not url:
            return HTMLResponse(
                render_capture(
                    url=str(brief.get("url") or ""),
                    name=str(brief.get("businessName") or ""),
                    geo=str(brief.get("geo") or ""),
                    goal=str(brief.get("goal") or ""),
                    assets=str(brief.get("assetUris") or ""),
                    error="Paste a website or Google listing URL.",
                ),
                status_code=400,
            )
        try:
            created = create_campaign(brief, raw_text=raw)
        except ArmorBlocked as exc:
            raise HTTPException(
                status_code=403, detail={"error": "blocked", "verdict": exc.verdict}
            ) from exc
        accept = (request.headers.get("accept") or "").lower()
        if "application/json" in ctype or "application/json" in accept:
            return created
        return RedirectResponse(created["runPath"], status_code=303)

    @app.get("/r/{campaign_id}", response_class=HTMLResponse, name="run_room")
    def run_room(campaign_id: str, request: Request) -> HTMLResponse:
        if not _safe_campaign_id(campaign_id) or "-" not in campaign_id:
            raise HTTPException(400, "bad campaign id")
        campaign = ledger.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(404, "campaign not found")
        key = request.query_params.get("k")
        if not studio_check_key(campaign, key):
            raise HTTPException(403, "studio key required")
        return HTMLResponse(render_run(campaign_id, campaign, key=key or ""))

    _claim_root(app)


def _claim_root(app: FastAPI) -> None:
    """ADK DevServer registers GET / first (web=True). Capture form is the event door."""
    capture = None
    rest = []
    for route in app.router.routes:
        name = getattr(route, "name", None)
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if name == "capture_home":
            capture = route
            continue
        if path == "/" and "GET" in methods:
            continue
        rest.append(route)
    if capture is None:
        return
    app.router.routes[:] = [capture, *rest]


def _safe_campaign_id(campaign_id: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9-]{3,80}", campaign_id or ""))


_CONSOLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Mission Control · Leadsy Flock</title>
  <style>
    body { margin:0; background:#14181f; color:#f3eee6; font-family: system-ui, sans-serif; }
    main { width: min(960px, calc(100% - 2rem)); margin: 0 auto; padding: 2.5rem 0 4rem; }
    h1 { font-weight: 560; font-family: Georgia, serif; }
    .kicker { letter-spacing: .2em; font-size: 12px; color:#c4a574; font-weight: 600; }
    a { color:#c4a574; }
    table { width:100%; border-collapse: collapse; }
    th, td { text-align:left; padding: .7rem .4rem; border-bottom: 1px solid #2c3340; font-size: 14px; }
    .muted { color:#b7aea2; }
    .pill { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#c4a574; }
  </style>
</head>
<body>
<main>
  <p class="kicker">LEADSY FLOCK · MISSION CONTROL</p>
  <h1>Receipts</h1>
  <p class="muted">Live from Firestore via flock-api. Capture is <a href="/">/</a>. Delivery is
  <code>/r/{id}?k=</code> (studio also at <code>/s/{id}?k=</code>). Seeded kit:
  <a href="/demo">/demo</a> · <a href="/k/google-listing-eaf57cae">Glen's Bakehouse</a>. Founder burn: <code>/ops</code>.</p>
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
    const kit = c.kitPath ? ` <a href="${c.kitPath}">kit</a>` : "";
    return `<tr>
      <td><a href="#" data-id="${c.id}">${name}</a><div class="muted">${c.id}</div></td>
      <td class="pill">${c.status || ""}</td>
      <td class="muted">${(c.updatedAt || "").slice(0,19)}</td>
      <td>${land}${kit}</td>
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
    status: c.status, landingPath: c.landingPath, kitPath: c.kitPath, receipts: recs, hired: (c.engineConfig || {}).hired
  }, null, 2);
}
load();
</script>
</body>
</html>
"""

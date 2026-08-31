# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""HTTP surface for Mission Control, judges, landings, and Pub/Sub push."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

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
from app.arch_ui import render_html as render_arch
from app.blog_ui import POST as BLOG_MD
from app.blog_ui import render_html as render_blog
from app.dash_ui import render_html as render_dash
from app.trace_ui import render_html as render_trace
from app.video_ui import VIDEO as VIDEO_MD
from app.video_ui import render_html as render_video
from app.derive import download_name
from app.kit_ui import render_from_campaign
from app.lock import enabled as public_lock_on
from app.lock import install as install_public_lock
from app.lock import is_seed_id
from app.observe import snapshot as dash_snapshot
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

_FLOCK_DIR = Path(__file__).resolve().parent / "static" / "flock"
_FLOCK_ASSETS = {
    "hero.png",
    "hero.webp",
    "flo.png",
    "flo.webp",
    "bri.png",
    "bri.webp",
    "scout.png",
    "scout.webp",
    "inka.png",
    "inka.webp",
    "stella.png",
    "stella.webp",
    "theater.css",
    "theater.js",
    "kit.css",
    "dash.css",
    "dash.js",
    "architecture.png",
    "art-brief.json",
}
_FLOCK_MIME = {
    ".css": "text/css",
    ".js": "text/javascript",
    ".png": "image/png",
    ".webp": "image/webp",
    ".json": "application/json",
}


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
                "home": "/demo" if public_lock_on() else "/",
                "run": None if public_lock_on() else "/r/{id}?k=",
                "demo": "/demo",
                "seedKit": "/k/google-listing-eaf57cae",
                "seedLanding": "/l/google-listing-eaf57cae",
                "ops": "/ops",
                "dash": "/dash",
                "architecture": "/architecture",
                "blog": "/blog",
                "studio": None if public_lock_on() else "/s/{id}?k=",
            },
            "publicLock": public_lock_on(),
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
        _seed_only(campaign_id)
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
        _seed_only(campaign_id)
        campaign = ledger.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(404, "kit not published")
        try:
            live = render_from_campaign(campaign_id, campaign)
        except Exception:  # noqa: BLE001 — fall back to the stored paste page
            live = None
        if live:
            return HTMLResponse(live)
        if campaign.get("kitHtml"):
            return HTMLResponse(campaign["kitHtml"])
        raise HTTPException(404, "kit not published")

    @app.get("/dash", response_class=HTMLResponse)
    def dash() -> HTMLResponse:
        return HTMLResponse(render_dash())

    @app.get("/trace", response_class=HTMLResponse)
    def backend_trace() -> HTMLResponse:
        return HTMLResponse(render_trace())

    @app.get("/architecture", response_class=HTMLResponse)
    def architecture() -> HTMLResponse:
        return HTMLResponse(render_arch())

    @app.get("/blog", response_class=HTMLResponse)
    def blog() -> HTMLResponse:
        return HTMLResponse(render_blog())

    @app.get("/blog.md")
    def blog_markdown() -> FileResponse:
        if not BLOG_MD.is_file():
            raise HTTPException(404, "blog missing")
        return FileResponse(
            BLOG_MD,
            media_type="text/markdown; charset=utf-8",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/video", response_class=HTMLResponse)
    def video_bible() -> HTMLResponse:
        return HTMLResponse(render_video())

    @app.get("/video.md")
    def video_markdown() -> FileResponse:
        if not VIDEO_MD.is_file():
            raise HTTPException(404, "video bible missing")
        return FileResponse(
            VIDEO_MD,
            media_type="text/markdown; charset=utf-8",
            headers={"Cache-Control": "public, max-age=60"},
        )

    @app.get("/architecture.png")
    def architecture_png() -> FileResponse:
        path = _FLOCK_DIR / "architecture.png"
        if not path.is_file():
            path = Path(__file__).resolve().parents[1] / "docs" / "architecture.png"
        if not path.is_file():
            raise HTTPException(404, "architecture diagram missing")
        return FileResponse(
            path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/v1/dash")
    def dash_json() -> dict:
        return dash_snapshot()

    @app.get("/v1/trace")
    def trace_json() -> dict:
        from app.observe import backend_path, cloud_run_proof

        return {"path": backend_path(), "run": cloud_run_proof(live=False)}

    @app.get("/console", response_class=HTMLResponse)
    def console() -> HTMLResponse:
        return RedirectResponse("/dash", status_code=303)

    @app.get("/media/{campaign_id}/still")
    def campaign_still(campaign_id: str) -> Response:
        _seed_only(campaign_id)
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
        _seed_only(campaign_id)
        if not _safe_campaign_id(campaign_id):
            raise HTTPException(400, "bad campaign id")
        return {
            slot: media.campaign_asset_exists(campaign_id, names)
            for slot, names in media.MEDIA_SLOTS.items()
        }

    @app.api_route("/media/{campaign_id}/{slot}", methods=["GET", "HEAD"])
    def campaign_media_slot(campaign_id: str, slot: str, request: Request) -> Response:
        _seed_only(campaign_id)
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
                play=q.get("play") or "",
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

    @app.get("/assets/flock/{name}")
    def flock_asset(name: str) -> FileResponse:
        if name not in _FLOCK_ASSETS:
            raise HTTPException(404, "unknown flock asset")
        path = _FLOCK_DIR / name
        if not path.is_file():
            raise HTTPException(404, "missing flock asset")
        mime = _FLOCK_MIME.get(path.suffix, "application/octet-stream")
        return FileResponse(path, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})

    install_public_lock(app)
    _claim_root(app)


def _seed_only(campaign_id: str) -> None:
    if public_lock_on() and not is_seed_id(campaign_id):
        raise HTTPException(404, "not published")


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

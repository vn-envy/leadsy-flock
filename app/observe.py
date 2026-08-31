# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Hackathon observatory: ledger health, seed burn, Cloud Run proof. No tables."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app import ledger
from app.settings import load_settings


def snapshot(*, live: bool = True) -> dict[str, Any]:
    campaigns = _campaigns()
    steps = Counter()
    statuses = Counter()
    hits_by = []
    for row in campaigns:
        statuses[str(row.get("status") or "unknown")] += 1
        for rec in row.get("receipts") or []:
            key = f"{rec.get('step') or '?'}"
            st = rec.get("status") or "unknown"
            steps[f"{key}:{st}"] += 1
        hits_by.append(
            {
                "id": row["id"],
                "name": row["name"],
                "hits": int(row.get("hits") or 0),
                "status": row.get("status"),
                "kitPath": row.get("kitPath") or f"/k/{row['id']}",
            }
        )
    hits_by.sort(key=lambda r: r["hits"], reverse=True)
    run = cloud_run_proof(live=live)
    traffic = run.get("requests") or {}
    seed = seed_trace()
    path = backend_path()
    return {
        "generatedAt": datetime.now(UTC).isoformat(),
        "totals": {
            "campaigns": len(campaigns),
            "completed": statuses.get("completed", 0),
            "running": statuses.get("running", 0),
            "planned": statuses.get("planned", 0),
            "hits": sum(r["hits"] for r in hits_by),
            "requests1h": traffic.get("count"),
            "latencyMsP50": traffic.get("p50ms"),
            "latencyMsP95": traffic.get("p95ms"),
            "seedTokens": (seed.get("tokens") or {}).get("total"),
            "seedCalls": seed.get("calls"),
            "seedUsd": seed.get("estimatedUsd"),
        },
        "status": [{"id": k, "n": v} for k, v in statuses.most_common()],
        "engines": _engine_bars(steps),
        "hits": hits_by[:8],
        "seed": seed,
        "path": path,
        "run": run,
        "note": "Public observatory. Seed burn is Vertex list price, not an invoice. We do not autopost.",
    }


def seed_trace() -> dict[str, Any]:
    from app.cost import public_trace
    from app.seed import DEMO_SHOP

    cid = str(DEMO_SHOP["campaignId"])
    try:
        receipts = ledger.list_receipts(cid)
    except Exception:  # noqa: BLE001
        receipts = []
    if not isinstance(receipts, list):
        receipts = []
    try:
        campaign = ledger.get_campaign(cid)
    except Exception:  # noqa: BLE001
        campaign = None
    if not isinstance(campaign, dict):
        campaign = {}
    trace = public_trace(cid, receipts, campaign)
    trace["name"] = str((campaign.get("brief") or {}).get("businessName") or DEMO_SHOP["name"])
    trace["kitPath"] = str(campaign.get("kitPath") or DEMO_SHOP["kitPath"])
    return trace


def cloud_run_proof(*, live: bool = True) -> dict[str, Any]:
    s = load_settings()
    service = os.environ.get("K_SERVICE") or "flock-api"
    proof: dict[str, Any] = {
        "service": service,
        "revision": os.environ.get("K_REVISION") or "local",
        "configuration": os.environ.get("K_CONFIGURATION") or "",
        "region": s.region,
        "project": s.project_id,
        "url": os.environ.get("APP_URL") or "",
        "source": "env",
        "image": "",
        "ready": os.environ.get("K_REVISION") is not None,
        "trafficPercent": 100 if os.environ.get("K_REVISION") else 0,
        "requests": {},
    }
    proof["console"] = console_links(s.project_id, s.region)
    if not live or not s.project_id:
        return proof
    described = _run_service(s.project_id, s.region, service)
    if described:
        proof.update(described)
        proof["source"] = "run.googleapis.com"
    proof["requests"] = _run_metrics(s.project_id, s.region, service)
    proof["console"] = console_links(s.project_id, s.region)
    return proof


_PATH_ORDER = (
    "plan",
    "approve",
    "scout",
    "inka",
    "inka_harvest",
    "creative_gate",
    "stella",
    "ad_kit",
)

_PATH_COPY = {
    "plan": "Bri quotes the kit. Flo still waits.",
    "approve": "Human YES on flock-api. Nothing expensive before this.",
    "scout": "Google Search + Maps + URL context. Evidence only.",
    "inka": "Copy + own-photo stills. Veo LRO starts; no wait.",
    "inka_harvest": "Poll Veo, mux English + Indic TTS, ffmpeg crops.",
    "creative_gate": "Regex + Gemma classifier + Gemini judge. Fail closed.",
    "stella": "Consent-first landing. Discovery is not consent.",
    "ad_kit": "Paste kit. autopost: false.",
}

_SPAN = {
    "plan": "campaign.plan",
    "approve": "campaign.approve",
    "scout": "engine.scout",
    "inka": "engine.inka",
    "inka_harvest": "engine.inka_harvest",
    "creative_gate": "engine.creative_gate",
    "stella": "engine.stella",
    "ad_kit": "engine.ad_kit",
}


def console_links(project: str, region: str) -> dict[str, str]:
    if not project:
        return {}
    worker_q = (
        'resource.type="cloud_run_revision"\n'
        'resource.labels.service_name="flock-worker"'
    )
    return {
        "apiTraces": (
            f"https://console.cloud.google.com/run/detail/{region}/flock-api"
            f"/observability/traces?project={project}"
        ),
        "workerTraces": (
            f"https://console.cloud.google.com/run/detail/{region}/flock-worker"
            f"/observability/traces?project={project}"
        ),
        "traceExplorer": f"https://console.cloud.google.com/traces/explorer?project={project}",
        "workerLogs": (
            "https://console.cloud.google.com/logs/query;query="
            f"{quote(worker_q, safe='')}?project={project}"
        ),
        "filter": 'span_name:"engine." campaign.id="google-listing-eaf57cae"',
    }


def backend_path() -> dict[str, Any]:
    from app.seed import DEMO_SHOP

    cid = str(DEMO_SHOP["campaignId"])
    try:
        receipts = ledger.list_receipts(cid)
    except Exception:  # noqa: BLE001
        receipts = []
    if not isinstance(receipts, list):
        receipts = []
    by_step = {
        str(r.get("step") or ""): r
        for r in receipts
        if isinstance(r, dict) and r.get("step")
    }
    hops = []
    for i, step in enumerate(_PATH_ORDER, start=1):
        rec = by_step.get(step) or {}
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        hops.append(
            {
                "n": i,
                "step": step,
                "engine": rec.get("engine") or _SPAN[step].split(".", 1)[-1],
                "status": rec.get("status") or "missing",
                "attempt": rec.get("attempt") or 1,
                "service": rec.get("service") or (
                    "flock-api" if step in {"plan", "approve"} else "flock-worker"
                ),
                "span": _SPAN[step],
                "startedAt": _when(rec.get("createdAt") or rec.get("updatedAt")),
                "finishedAt": _when(rec.get("updatedAt")),
                "model": _hop_model(step, payload),
                "traceId": str(payload.get("traceId") or rec.get("traceId") or ""),
                "say": _PATH_COPY[step],
            }
        )
    s = load_settings()
    return {
        "campaignId": cid,
        "name": DEMO_SHOP["name"],
        "hops": hops,
        "console": console_links(s.project_id, s.region),
        "note": (
            "Firestore receipts for the seeded Glen's run. Worker spans are "
            "engine.<step> on Cloud Run flock-worker. Console links need a "
            "Google account on this GCP project. We do not autopost."
        ),
    }


def _when(value: Any) -> str:
    if value is None or value == "":
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:  # noqa: BLE001
            return str(value)
    return str(value)


def _hop_model(step: str, payload: dict[str, Any]) -> str:
    model = str(payload.get("model") or "").strip()
    if model:
        return model
    if step == "creative_gate":
        return "gemma + gemini-3.5-flash judge"
    if step == "inka_harvest":
        return "veo-3.1-generate-001 + gemini tts"
    if step == "ad_kit":
        return "ffmpeg"
    if step == "stella":
        return "template"
    if step in {"plan", "approve"}:
        return "gemini-3.5-flash"
    return ""


def _campaigns() -> list[dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor

    try:
        rows = ledger.list_campaigns(limit=40)
    except Exception:  # noqa: BLE001 — dash must still render Cloud Run proof
        return []
    if not isinstance(rows, list):
        return []
    jobs = [c for c in rows if isinstance(c, dict) and c.get("id")]
    if not jobs:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        return [row for row in pool.map(_campaign_row, jobs) if row]


def _campaign_row(c: dict[str, Any]) -> dict[str, Any] | None:
    cid = str(c.get("id") or "")
    if not cid:
        return None
    try:
        receipts = ledger.list_receipts(cid)
    except Exception:  # noqa: BLE001
        receipts = []
    if not isinstance(receipts, list):
        receipts = []
    try:
        hits = ledger.list_events(cid, kind="landing_hit")
    except Exception:  # noqa: BLE001
        hits = []
    hit_n = len(hits) if isinstance(hits, list) else 0
    recs = [
        {"step": r.get("step"), "status": r.get("status")}
        for r in receipts
        if isinstance(r, dict)
    ]
    return {
        "id": cid,
        "name": (c.get("brief") or {}).get("businessName") or cid,
        "status": c.get("status"),
        "kitPath": c.get("kitPath"),
        "hits": hit_n,
        "receipts": recs,
    }


def _engine_bars(steps: Counter[str]) -> list[dict[str, Any]]:
    names = ("scout", "inka", "inka_harvest", "creative_gate", "stella", "ad_kit")
    bars = []
    for name in names:
        ok = steps.get(f"{name}:ok", 0)
        started = steps.get(f"{name}:started", 0)
        other = sum(v for k, v in steps.items() if k.startswith(name + ":") and not k.endswith(":ok") and not k.endswith(":started"))
        bars.append({"id": name, "ok": ok, "running": started, "other": other, "n": ok + started + other})
    return bars


def _run_service(project: str, region: str, service: str) -> dict[str, Any] | None:
    url = f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/services/{service}"
    body = _gcp_get(url)
    if not body:
        return None
    template = body.get("template") or {}
    containers = template.get("containers") or []
    image = ""
    if containers and isinstance(containers[0], dict):
        image = str(containers[0].get("image") or "")
    traffic = body.get("traffic") or []
    pct = 0
    for t in traffic:
        if isinstance(t, dict):
            pct += int(t.get("percent") or 0)
    conds = body.get("terminalCondition") or body.get("conditions") or {}
    ready = False
    if isinstance(conds, dict):
        ready = str(conds.get("state") or "") in {"CONDITION_SUCCEEDED", "True"}
    elif isinstance(conds, list):
        ready = any(
            isinstance(c, dict) and c.get("type") == "Ready" and str(c.get("state") or c.get("status") or "") in {"CONDITION_SUCCEEDED", "True"}
            for c in conds
        )
    return {
        "url": str(body.get("uri") or ""),
        "revision": str(body.get("latestReadyRevision") or "").rsplit("/", 1)[-1],
        "image": image,
        "trafficPercent": pct or 100,
        "ready": ready or bool(body.get("latestReadyRevision")),
        "uid": str(body.get("uid") or ""),
        "reconciling": bool(body.get("reconciling")),
    }


def _run_metrics(project: str, region: str, service: str) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor

    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    filt = (
        'metric.type="run.googleapis.com/request_count" '
        f'AND resource.labels.service_name="{service}" '
        f'AND resource.labels.location="{region}"'
    )
    lat_filt = (
        'metric.type="run.googleapis.com/request_latencies" '
        f'AND resource.labels.service_name="{service}" '
        f'AND resource.labels.location="{region}"'
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_count = pool.submit(_timeseries, project, filt, start, end, aligner="ALIGN_SUM")
        f_p50 = pool.submit(_timeseries, project, lat_filt, start, end, aligner="ALIGN_PERCENTILE_50")
        f_p95 = pool.submit(_timeseries, project, lat_filt, start, end, aligner="ALIGN_PERCENTILE_95")
        count = f_count.result()
        p50 = f_p50.result()
        p95 = f_p95.result()
    out: dict[str, Any] = {}
    if count is not None:
        out["count"] = int(count)
    if p50 is not None:
        out["p50ms"] = round(float(p50), 1)
    if p95 is not None:
        out["p95ms"] = round(float(p95), 1)
    return out


def _timeseries(
    project: str,
    filt: str,
    start: datetime,
    end: datetime,
    *,
    aligner: str,
) -> float | None:
    q = urlencode(
        {
            "filter": filt,
            "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "interval.endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "aggregation.alignmentPeriod": "3600s",
            "aggregation.perSeriesAligner": aligner,
            "aggregation.crossSeriesReducer": "REDUCE_SUM",
        }
    )
    body = _gcp_get(f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?{q}")
    if not body:
        return None
    series = body.get("timeSeries") or []
    total = 0.0
    found = False
    for item in series:
        points = item.get("points") or []
        if not points:
            continue
        val = (points[0].get("value") or {})
        if "int64Value" in val:
            total += float(val["int64Value"])
            found = True
        elif "doubleValue" in val:
            total += float(val["doubleValue"])
            found = True
        elif "distributionValue" in val:
            mean = ((val.get("distributionValue") or {}).get("mean"))
            if mean is not None:
                total += float(mean)
                found = True
    return total if found else None


def _gcp_get(url: str, timeout: float = 1.8) -> dict[str, Any] | None:
    try:
        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        req = Request(url, headers={"Authorization": f"Bearer {creds.token}"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Hackathon observatory: ledger health + Cloud Run proof. No prices. No tables."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
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
        },
        "status": [{"id": k, "n": v} for k, v in statuses.most_common()],
        "engines": _engine_bars(steps),
        "hits": hits_by[:8],
        "run": run,
        "note": "Public observatory. No prices. We do not autopost.",
    }


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
    if not live or not s.project_id:
        return proof
    described = _run_service(s.project_id, s.region, service)
    if described:
        proof.update(described)
        proof["source"] = "run.googleapis.com"
    proof["requests"] = _run_metrics(s.project_id, s.region, service)
    return proof


def _campaigns() -> list[dict[str, Any]]:
    try:
        rows = ledger.list_campaigns(limit=40)
    except Exception:  # noqa: BLE001 — dash must still render Cloud Run proof
        return []
    if not isinstance(rows, list):
        return []
    out = []
    for c in rows:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        if not cid:
            continue
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
        out.append(
            {
                "id": cid,
                "name": (c.get("brief") or {}).get("businessName") or cid,
                "status": c.get("status"),
                "kitPath": c.get("kitPath"),
                "hits": hit_n,
                "receipts": recs,
            }
        )
    return out


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

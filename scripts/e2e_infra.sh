#!/usr/bin/env bash
# End-to-end infra skeleton: screen → create → approve → wait for receipts.
set -euo pipefail

API_URL="${FLOCK_API_URL:?set FLOCK_API_URL}"
API_URL="${API_URL%/}"

echo "==> GET /health"
curl -sfS "${API_URL}/health"
echo

echo "==> GET /v1/infra"
curl -sfS "${API_URL}/v1/infra"
echo

echo "==> POST /v1/screen"
curl -sfS -X POST "${API_URL}/v1/screen" \
  -H 'content-type: application/json' \
  -d '{"text":"I run Peak Gym in Gurgaon and want 40 evening members."}'
echo

echo "==> POST /v1/campaigns"
CREATED=$(curl -sfS -X POST "${API_URL}/v1/campaigns" \
  -H 'content-type: application/json' \
  -d '{"brief":{"businessName":"Peak Gym","geo":"Gurgaon","goal":"40 evening members from working professionals","budgetInr":8000,"audience":"office workers near Golf Course Road"}}')
echo "${CREATED}"
CAMPAIGN_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${CREATED}")

echo "==> POST /v1/campaigns/${CAMPAIGN_ID}/approve"
curl -sfS -X POST "${API_URL}/v1/campaigns/${CAMPAIGN_ID}/approve"
echo

export API_URL="${API_URL}"
export CAMPAIGN_ID="${CAMPAIGN_ID}"
echo "==> wait for receipts (Scout → Inka → Gate → Stella → Ad Kit)"
python3 - <<'PY'
import json, time, urllib.request, os, sys
from pathlib import Path

api = os.environ["API_URL"]
cid = os.environ["CAMPAIGN_ID"]
url = api + "/v1/campaigns/" + cid
want = {"plan", "approve", "scout", "inka", "creative_gate", "stella", "ad_kit"}
last = None
for i in range(90):
    with urllib.request.urlopen(url, timeout=20) as resp:
        body = json.loads(resp.read().decode())
    last = body
    ok = {r.get("step") for r in body.get("receipts") or [] if r.get("status") == "ok"}
    print(f"try {i} status={body.get('status')} ok={sorted(ok)}", flush=True)
    if want <= ok:
        break
    time.sleep(8)
else:
    print(json.dumps(last, indent=2))
    sys.exit(1)

landing = api + "/l/" + cid
with urllib.request.urlopen(landing, timeout=20) as resp:
    html = resp.read().decode()
assert "consent first" in html
assert f"/media/{cid}/still" in html, "Stella page is missing the still <img>"
still_url = api + "/media/" + cid + "/still"
with urllib.request.urlopen(still_url, timeout=30) as resp:
    still_type = resp.headers.get("Content-Type") or ""
    still_bytes = len(resp.read())
assert still_type.startswith("image/") and still_bytes > 1000, f"still missing: {still_type} {still_bytes}"
still_ok = True
assert f"/media/{cid}/clip" in html, "Stella page is missing the clip <video>"
assert f"/media/{cid}/jingle" in html, "Stella page is missing the jingle <audio>"
consent_req = urllib.request.Request(
    api + "/v1/consents",
    data=json.dumps({
        "campaignId": cid,
        "name": "Judge Demo",
        "contact": "judge@example.test",
        "consent": True,
        "source": "e2e",
    }).encode(),
    headers={"content-type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(consent_req, timeout=20) as resp:
    consent = json.loads(resp.read().decode())

with urllib.request.urlopen(url, timeout=20) as resp:
    last = json.loads(resp.read().decode())

gate = next(r for r in last["receipts"] if r.get("step") == "creative_gate")
scout = next(r for r in last["receipts"] if r.get("step") == "scout")
inka = next(r for r in last["receipts"] if r.get("step") == "inka")
inka_assets = (inka.get("payload") or {}).get("assets") or {}
harvest_rows = [r for r in last.get("receipts") or [] if r.get("step") == "inka_harvest"]
need_harvest = bool((inka_assets.get("clip") or {}).get("operation") or (inka_assets.get("jingle") or {}).get("pending"))
if need_harvest and not harvest_rows:
    print("harvest sidecar never started", flush=True)
    sys.exit(1)

clip_url = api + "/media/" + cid + "/clip"
jingle_url = api + "/media/" + cid + "/jingle"
clip_ok = False
clip_bytes = 0
clip_type = ""
jingle_ok = False
jingle_bytes = 0
jingle_type = ""

def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return resp.headers.get("Content-Type") or "", len(resp.read()), True
    except Exception:
        return "", 0, False

for i in range(24):
    clip_type, clip_bytes, clip_ok = _get(clip_url)
    jingle_type, jingle_bytes, jingle_ok = _get(jingle_url)
    with urllib.request.urlopen(url, timeout=20) as resp:
        last = json.loads(resp.read().decode())
    harvest_rows = [r for r in last.get("receipts") or [] if r.get("step") == "inka_harvest"]
    print(
        f"harvest try {i} clip={clip_ok}/{clip_bytes} jingle={jingle_ok}/{jingle_bytes} "
        f"harvest={[(r.get('status'), r.get('attempt')) for r in harvest_rows]}",
        flush=True,
    )
    if clip_ok and clip_type.startswith("video/") and clip_bytes > 1000:
        break
    harvest_done = any(r.get("status") == "ok" for r in harvest_rows)
    if harvest_done and not clip_ok:
        break
    time.sleep(8)

summary = {
    "campaignId": cid,
    "status": last.get("status"),
    "landing": landing,
    "still": {"url": still_url, "ok": still_ok, "bytes": still_bytes, "contentType": still_type},
    "clip": {"url": clip_url, "ok": clip_ok, "bytes": clip_bytes, "contentType": clip_type},
    "jingle": {"url": jingle_url, "ok": jingle_ok, "bytes": jingle_bytes, "contentType": jingle_type},
    "harvest": [
        {"status": r.get("status"), "attempt": r.get("attempt"), "payload": r.get("payload") or {}}
        for r in harvest_rows
    ],
    "consent": consent,
    "gate": (gate.get("payload") or {}),
    "scoutGrounding": (scout.get("payload") or {}).get("groundingUris") or [],
    "inkaAssets": inka_assets,
    "draftRejected": ((gate.get("payload") or {}).get("draft") or {}).get("rejected"),
    "gateVerdict": (gate.get("payload") or {}).get("verdict"),
}
out = Path("proof/engines")
out.mkdir(parents=True, exist_ok=True)
(out / "e2e-campaign.json").write_text(json.dumps(last, indent=2) + "\n")
(out / "e2e-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print("PASS", json.dumps({
    "campaignId": cid,
    "verdict": summary["gateVerdict"],
    "draftRejected": summary["draftRejected"],
    "stillBytes": still_bytes,
    "clipBytes": clip_bytes,
    "jingleBytes": jingle_bytes,
    "harvestStatus": [r.get("status") for r in harvest_rows],
}))
PY

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
summary = {
    "campaignId": cid,
    "status": last.get("status"),
    "landing": landing,
    "consent": consent,
    "gate": (gate.get("payload") or {}),
    "scoutGrounding": (scout.get("payload") or {}).get("groundingUris") or [],
    "inkaAssets": (inka.get("payload") or {}).get("assets") or {},
    "draftRejected": ((gate.get("payload") or {}).get("draft") or {}).get("rejected"),
    "gateVerdict": (gate.get("payload") or {}).get("verdict"),
}
out = Path("proof/engines")
out.mkdir(parents=True, exist_ok=True)
(out / "e2e-campaign.json").write_text(json.dumps(last, indent=2) + "\n")
(out / "e2e-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print("PASS", json.dumps({"campaignId": cid, "verdict": summary["gateVerdict"], "draftRejected": summary["draftRejected"]}))
PY

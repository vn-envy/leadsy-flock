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
echo "==> wait for receipts"
python3 - <<'PY'
import json, time, urllib.request, os, sys
url = os.environ["API_URL"] + "/v1/campaigns/" + os.environ["CAMPAIGN_ID"]
want = {"plan", "approve", "scout"}
last = None
for i in range(24):
    with urllib.request.urlopen(url, timeout=20) as resp:
        body = json.loads(resp.read().decode())
    last = body
    steps = {r.get("step") for r in body.get("receipts") or []}
    ok = {r.get("step") for r in body.get("receipts") or [] if r.get("status") == "ok"}
    print(f"try {i} status={body.get('status')} steps={sorted(steps)} ok={sorted(ok)}", flush=True)
    if want <= ok:
        Path = __import__("pathlib").Path
        out = Path("proof/infra")
        out.mkdir(parents=True, exist_ok=True)
        (out / "e2e-campaign.json").write_text(json.dumps(body, indent=2) + "\n")
        print("PASS")
        sys.exit(0)
    time.sleep(5)
print(json.dumps(last, indent=2))
sys.exit(1)
PY

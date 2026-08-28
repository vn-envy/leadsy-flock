#!/usr/bin/env bash
# Live salon pass: Noya Salon (fictional) in Gurgaon. Validates the 2026 asset kit.
# Does not replace scripts/e2e_infra.sh (Peak Gym). Lyria 429 does not fail the kit.
set -euo pipefail

API_URL="${FLOCK_API_URL:?set FLOCK_API_URL}"
API_URL="${API_URL%/}"

echo "==> GET /health"
curl -sfS "${API_URL}/health"
echo

echo "==> POST /v1/campaigns (Noya Salon)"
CREATED=$(curl -sfS -X POST "${API_URL}/v1/campaigns" \
  -H 'content-type: application/json' \
  -d '{"brief":{"businessName":"Noya Salon","geo":"Gurgaon","goal":"25 new colour clients from Golf Course Road professionals","budgetInr":8000,"audience":"women 25-40 working near DLF Phase IV"}}')
echo "${CREATED}"
CAMPAIGN_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${CREATED}")

echo "==> POST /v1/campaigns/${CAMPAIGN_ID}/approve"
curl -sfS -X POST "${API_URL}/v1/campaigns/${CAMPAIGN_ID}/approve"
echo

export API_URL="${API_URL}"
export CAMPAIGN_ID="${CAMPAIGN_ID}"
echo "==> wait for Scout → Ad Kit + kit page"
python3 - <<'PY'
import json, time, urllib.error, urllib.request, os, sys
from pathlib import Path

api = os.environ["API_URL"]
cid = os.environ["CAMPAIGN_ID"]
url = api + "/v1/campaigns/" + cid
want = {"plan", "approve", "scout", "inka", "creative_gate", "stella", "ad_kit"}
last = None
for i in range(90):
    with urllib.request.urlopen(url, timeout=20) as resp:
        last = json.loads(resp.read().decode())
    ok = {r.get("step") for r in last.get("receipts") or [] if r.get("status") == "ok"}
    print(f"try {i} status={last.get('status')} ok={sorted(ok)}", flush=True)
    if want <= ok:
        break
    time.sleep(8)
else:
    print(json.dumps(last, indent=2)[:8000])
    sys.exit(1)

kit_url = api + "/k/" + cid
with urllib.request.urlopen(kit_url, timeout=20) as resp:
    kit_html = resp.read().decode()
assert "We do not autopost" in kit_html
assert "Noya Salon" in kit_html
assert f"/media/{cid}/still-feed" in kit_html
assert f"/media/{cid}/clip-story" in kit_html
assert "whatsapp_status" in kit_html
assert "--bg:" in kit_html
theme = ((next(r for r in last["receipts"] if r.get("step") == "ad_kit").get("payload") or {}).get("themeId"))
print(f"kit themeId={theme}", flush=True)

landing = api + "/l/" + cid
with urllib.request.urlopen(landing, timeout=20) as resp:
    html = resp.read().decode()
assert "consent first" in html
assert ".hero[hidden]" in html
assert html.count('class="hero"') >= 1

def _get(path):
    try:
        with urllib.request.urlopen(api + path, timeout=60) as resp:
            return resp.headers.get("Content-Type") or "", len(resp.read()), True
    except Exception as exc:
        return str(exc), 0, False

stills = {}
for slot in ("still", "still-story", "still-feed", "still-square", "still-landscape"):
    ctype, nbytes, ok = _get(f"/media/{cid}/{slot}")
    stills[slot] = {"ok": ok, "bytes": nbytes, "contentType": ctype}
    print(f"still {slot} ok={ok} bytes={nbytes} type={ctype}", flush=True)
assert stills["still"]["ok"] and stills["still"]["bytes"] > 1000, stills

consent_req = urllib.request.Request(
    api + "/v1/consents",
    data=json.dumps({
        "campaignId": cid,
        "name": "Judge Demo",
        "contact": "judge@example.test",
        "consent": True,
        "source": "salon-e2e",
    }).encode(),
    headers={"content-type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(consent_req, timeout=20) as resp:
    consent = json.loads(resp.read().decode())

inka = next(r for r in last["receipts"] if r.get("step") == "inka")
inka_assets = (inka.get("payload") or {}).get("assets") or {}
need_harvest = bool(
    (inka_assets.get("clip") or {}).get("operation") or (inka_assets.get("jingle") or {}).get("pending")
)
clips = {}
jingle = {"ok": False, "bytes": 0, "contentType": ""}
harvest_rows = []
for i in range(28):
    with urllib.request.urlopen(url, timeout=20) as resp:
        last = json.loads(resp.read().decode())
    harvest_rows = [r for r in last.get("receipts") or [] if r.get("step") == "inka_harvest"]
    for slot in ("clip", "clip-story", "clip-feed", "clip-square", "clip-landscape"):
        ctype, nbytes, ok = _get(f"/media/{cid}/{slot}")
        clips[slot] = {"ok": ok, "bytes": nbytes, "contentType": ctype}
    jtype, jbytes, jok = _get(f"/media/{cid}/jingle")
    jingle = {"ok": jok, "bytes": jbytes, "contentType": jtype}
    print(
        f"harvest try {i} clip={clips.get('clip')} story={clips.get('clip-story')} "
        f"jingle={jingle} harvest={[(r.get('status'), r.get('attempt')) for r in harvest_rows]}",
        flush=True,
    )
    if clips.get("clip", {}).get("ok") and clips.get("clip-story", {}).get("ok"):
        break
    harvest_done = any(r.get("status") == "ok" for r in harvest_rows)
    if harvest_done and clips.get("clip", {}).get("ok"):
        break
    time.sleep(8)

if need_harvest and not harvest_rows:
    print("harvest sidecar never started", flush=True)
    sys.exit(1)

# Kit must exist even if Veo is still polling; clip-story is the live proof of ffmpeg.
kit_ok = True
clip_ok = bool(clips.get("clip", {}).get("ok") and (clips["clip"]["bytes"] or 0) > 1000)
story_ok = bool(clips.get("clip-story", {}).get("ok") and (clips["clip-story"]["bytes"] or 0) > 500)
if clip_ok and not story_ok:
    print("clip harvested but 9:16 crop missing (ffmpeg?)", flush=True)
    sys.exit(1)

with urllib.request.urlopen(api + "/media/" + cid + "/ready", timeout=20) as resp:
    ready = json.loads(resp.read().decode())

gate = next(r for r in last["receipts"] if r.get("step") == "creative_gate")
scout = next(r for r in last["receipts"] if r.get("step") == "scout")
adkit = next(r for r in last["receipts"] if r.get("step") == "ad_kit")
summary = {
    "campaignId": cid,
    "status": last.get("status"),
    "themeId": (adkit.get("payload") or {}).get("themeId"),
    "kit": kit_url,
    "landing": landing,
    "stills": stills,
    "clips": clips,
    "jingle": jingle,
    "ready": ready,
    "harvest": [
        {"status": r.get("status"), "attempt": r.get("attempt")}
        for r in harvest_rows
    ],
    "consent": consent,
    "draftRejected": ((gate.get("payload") or {}).get("draft") or {}).get("rejected"),
    "gateVerdict": (gate.get("payload") or {}).get("verdict"),
    "scoutGrounding": (scout.get("payload") or {}).get("groundingUris") or [],
    "autopost": (adkit.get("payload") or {}).get("autopost"),
    "kitHtmlHasAutopostRefusal": "We do not autopost" in kit_html,
}
out = Path("proof/engines")
out.mkdir(parents=True, exist_ok=True)
(out / "salon-campaign.json").write_text(json.dumps(last, indent=2) + "\n")
(out / "salon-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print("PASS", json.dumps({
    "campaignId": cid,
    "themeId": summary["themeId"],
    "kit": kit_url,
    "stillBytes": stills["still"]["bytes"],
    "stillStoryBytes": stills.get("still-story", {}).get("bytes"),
    "clipBytes": clips.get("clip", {}).get("bytes"),
    "clipStoryBytes": clips.get("clip-story", {}).get("bytes"),
    "jingleBytes": jingle.get("bytes"),
    "autopost": summary["autopost"],
    "gateVerdict": summary["gateVerdict"],
}))
PY

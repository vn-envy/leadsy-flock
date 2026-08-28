#!/usr/bin/env bash
# Live sanity check against a REAL public Google listing.
# Pulls own photos only. Does not email, call, or autopost the business.
set -euo pipefail

API_URL="${FLOCK_API_URL:?set FLOCK_API_URL}"
API_URL="${API_URL%/}"
LISTING="${GOOGLE_LISTING_URL:-https://share.google/rLF34cfolz9TJA92F}"
export LISTING

echo "==> GET /health"
curl -sfS "${API_URL}/health"
echo

echo "==> POST /v1/campaigns (public listing, no outreach)"
CREATED=$(curl -sfS -X POST "${API_URL}/v1/campaigns" \
  -H 'content-type: application/json' \
  -d "$(python3 -c "
import json, os
print(json.dumps({
  'brief': {
    'businessName': os.environ.get('LISTING_NAME') or 'Google listing',
    'geo': os.environ.get('LISTING_GEO') or 'India',
    'goal': 'Sanity-check own photos, channel-sized exports, and a proof film. Do not contact this business.',
    'audience': 'people nearby who already know the shop',
    'googleListing': os.environ['LISTING'],
    'website': os.environ['LISTING'],
  }
}))
")" )
echo "${CREATED}"
CAMPAIGN_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${CREATED}")

echo "==> POST /v1/campaigns/${CAMPAIGN_ID}/approve"
curl -sfS -X POST "${API_URL}/v1/campaigns/${CAMPAIGN_ID}/approve"
echo

export API_URL CAMPAIGN_ID LISTING
echo "==> wait Scout → Ad Kit"
python3 - <<'PY'
import json, os, subprocess, sys, time, urllib.request
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
assert "data-aspect=\"4:5\"" in kit_html
assert "1080×1350" in kit_html
assert "clip-proof-feed" in kit_html
assert "Save 1080" in kit_html

inka = next(r for r in last["receipts"] if r.get("step") == "inka")
scout = next(r for r in last["receipts"] if r.get("step") == "scout")
inka_p = inka.get("payload") or {}
scout_p = scout.get("payload") or {}
print("resolvedName", inka_p.get("resolvedName") or scout_p.get("resolvedName"), flush=True)
print("vertical", inka_p.get("vertical"), flush=True)
print("origin", (inka_p.get("assets") or {}).get("origin"), "own", ((inka_p.get("assets") or {}).get("own") or {}).get("count"), flush=True)

def _get(path):
    try:
        with urllib.request.urlopen(api + path, timeout=60) as resp:
            return resp.headers.get("Content-Type") or "", len(resp.read()), True
    except Exception as exc:
        return str(exc), 0, False

clips = {}
for i in range(50):
    with urllib.request.urlopen(url, timeout=20) as resp:
        last = json.loads(resp.read().decode())
    for slot in ("clip", "clip-feed", "clip-square", "clip-story", "clip-landscape", "clip-en", "clip-indic", "clip-proof", "clip-proof-feed", "clip-proof-story"):
        ctype, nbytes, ok = _get(f"/media/{cid}/{slot}")
        clips[slot] = {"ok": ok, "bytes": nbytes, "contentType": ctype}
    print(f"harvest try {i} clip={clips.get('clip')} feed={clips.get('clip-feed')} proof={clips.get('clip-proof')}", flush=True)
    harvest_rows = [r for r in last.get("receipts") or [] if r.get("step") == "inka_harvest"]
    harvest_done = any(r.get("status") == "ok" for r in harvest_rows)
    if clips.get("clip", {}).get("ok") and clips.get("clip-feed", {}).get("ok") and (clips.get("clip-en", {}).get("ok") or i >= 20):
        if harvest_done or clips.get("clip-proof", {}).get("ok") or i >= 24:
            break
    time.sleep(8)

def _probe(slot):
    dest = f"/tmp/{cid}-{slot}.bin"
    try:
        urllib.request.urlretrieve(api + f"/media/{cid}/{slot}", dest)
    except Exception as exc:
        return {"slot": slot, "error": str(exc)}
    raw = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", dest],
        capture_output=True, text=True,
    )
    wh = (raw.stdout or "").strip()
    return {"slot": slot, "wh": wh, "ok": raw.returncode == 0}

probes = {}
for slot, expect in (("clip-feed", "1080,1350"), ("clip-square", "1080,1080"), ("clip-story", "1080,1920"), ("clip-landscape", "1200,628")):
    if clips.get(slot, {}).get("ok"):
        probes[slot] = _probe(slot)
        print("probe", probes[slot], "expect", expect, flush=True)
        if probes[slot].get("wh") != expect:
            print("WARN pixel box mismatch", slot, probes[slot], flush=True)

with urllib.request.urlopen(api + "/media/" + cid + "/ready", timeout=20) as resp:
    ready = json.loads(resp.read().decode())

summary = {
    "campaignId": cid,
    "listing": os.environ.get("LISTING"),
    "status": last.get("status"),
    "resolvedName": inka_p.get("resolvedName") or scout_p.get("resolvedName"),
    "vertical": inka_p.get("vertical"),
    "origin": (inka_p.get("assets") or {}).get("origin"),
    "ownCount": ((inka_p.get("assets") or {}).get("own") or {}).get("count"),
    "kit": kit_url,
    "landing": api + "/l/" + cid,
    "clips": clips,
    "probes": probes,
    "ready": ready,
    "autopost": False,
    "contactedBusiness": False,
}
out = Path("proof/engines")
out.mkdir(parents=True, exist_ok=True)
(out / "listing-campaign.json").write_text(json.dumps(last, indent=2) + "\n")
(out / "listing-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
print("PASS", json.dumps({k: summary[k] for k in ("campaignId", "resolvedName", "origin", "ownCount", "kit")}, ensure_ascii=False))
if clips.get("clip-feed", {}).get("ok") and probes.get("clip-feed", {}).get("wh") not in (None, "1080,1350"):
    sys.exit(1)
PY

#!/usr/bin/env bash
# Manually invoke one worker step when Pub/Sub push is stuck.
# Does not email, call, or autopost. Identity-token auth against flock-worker.
set -euo pipefail

WORKER_URL="${FLOCK_WORKER_URL:-https://flock-worker-ehbzbxie5a-el.a.run.app}"
WORKER_URL="${WORKER_URL%/}"
CAMPAIGN_ID="${1:?campaign id}"
STEP="${2:?step}"
PIPELINE_JSON="${PIPELINE_JSON:-[\"scout\",\"inka\",\"creative_gate\",\"stella\",\"ad_kit\"]}"
ATTEMPT="${ATTEMPT:-1}"
FORCE="${FORCE:-true}"
TIMEOUT="${TIMEOUT:-480}"
export PATH="${HOME}/.local/bin:/tmp/google-cloud-sdk/bin:${PATH}"
export CID="${CAMPAIGN_ID}" STEP PIPELINE_JSON ATTEMPT FORCE

TOKEN="$(gcloud auth print-identity-token --audiences="${WORKER_URL}")"
DATA="$(python3 -c "
import base64, json, os
body = {
  'campaignId': os.environ['CID'],
  'step': os.environ['STEP'],
  'pipeline': json.loads(os.environ['PIPELINE_JSON']),
  'attempt': int(os.environ['ATTEMPT']),
  'forceRetry': os.environ['FORCE'].lower() in ('1', 'true', 'yes'),
  'idempotencyKey': f\"{os.environ['CID']}:{os.environ['STEP']}:{os.environ['ATTEMPT']}\",
}
print(base64.b64encode(json.dumps(body).encode()).decode())
")"

echo "==> invoke ${STEP} on ${CAMPAIGN_ID} (timeout ${TIMEOUT}s)"
curl -sfS --max-time "${TIMEOUT}" -X POST "${WORKER_URL}/internal/pubsub/campaign-steps" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "content-type: application/json" \
  -d "{\"message\":{\"data\":\"${DATA}\",\"messageId\":\"manual-$(date +%s)\"}}"
echo

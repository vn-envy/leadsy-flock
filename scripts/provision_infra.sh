#!/usr/bin/env bash
# Idempotent Google Cloud provisioner for Leadsy Flock.
# Requires gcloud auth as a principal that can create resources in GCP_PROJECT_ID.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${GCP_PROJECT_ID:-leadsy-flock}"
REGION="${GCP_REGION:-asia-south1}"
RUNTIME_REGION="${VERTEX_RUNTIME_REGION:-us-central1}"
SA="${GCP_SERVICE_ACCOUNT:-leadsy-agent@${PROJECT}.iam.gserviceaccount.com}"
PUSH_SA="leadsy-pubsub-push@${PROJECT}.iam.gserviceaccount.com"
ARMOR_TEMPLATE="${MODEL_ARMOR_TEMPLATE:-leadsy-inbound}"
MEDIA_BUCKET="${MEDIA_BUCKET_NAME:-${PROJECT}-media-${REGION}}"
LOGS_BUCKET="${LOGS_BUCKET_NAME:-${PROJECT}-logs-${REGION}}"
TOPIC="${CAMPAIGN_STEPS_TOPIC:-campaign-steps}"
DLQ="${CAMPAIGN_STEPS_DLQ_TOPIC:-campaign-steps-dlq}"
ALERTS="${FOUNDER_ALERTS_TOPIC:-founder-alerts}"
SUB="${CAMPAIGN_STEPS_SUBSCRIPTION:-campaign-steps-worker}"
WORKER_URL="${FLOCK_WORKER_URL:-}"

export PATH="${HOME}/.local/bin:/tmp/google-cloud-sdk/bin:${PATH}"
gcloud config set project "${PROJECT}" >/dev/null

echo "==> Enable APIs"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  modelarmor.googleapis.com \
  --project="${PROJECT}"

echo "==> Pub/Sub topics"
for t in "${TOPIC}" "${DLQ}" "${ALERTS}"; do
  if gcloud pubsub topics describe "${t}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "    topic ${t} exists"
  else
    gcloud pubsub topics create "${t}" --project="${PROJECT}"
  fi
done

echo "==> GCS buckets"
for b in "${MEDIA_BUCKET}" "${LOGS_BUCKET}"; do
  if gcloud storage buckets describe "gs://${b}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "    bucket ${b} exists"
  else
    gcloud storage buckets create "gs://${b}" \
      --project="${PROJECT}" \
      --location="${REGION}" \
      --uniform-bucket-level-access
  fi
done

echo "==> Model Armor template ${ARMOR_TEMPLATE} in ${REGION}"
if gcloud model-armor templates describe "${ARMOR_TEMPLATE}" \
    --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "    template exists"
else
  # asia-south1 does not support malicious-uri filters. RAI + PI/jailbreak only.
  gcloud model-armor templates create "${ARMOR_TEMPLATE}" \
    --location="${REGION}" \
    --project="${PROJECT}" \
    --rai-settings-filters=confidenceLevel=medium-and-above,filterType=hate-speech \
    --rai-settings-filters=confidenceLevel=medium-and-above,filterType=harassment \
    --rai-settings-filters=confidenceLevel=medium-and-above,filterType=sexually-explicit \
    --rai-settings-filters=confidenceLevel=medium-and-above,filterType=dangerous \
    --pi-and-jailbreak-filter-settings-enforcement=enabled \
    --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above
fi

echo "==> Pub/Sub push service account"
if gcloud iam service-accounts describe "${PUSH_SA}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "    ${PUSH_SA} exists"
else
  gcloud iam service-accounts create leadsy-pubsub-push \
    --project="${PROJECT}" \
    --display-name="Leadsy Pub/Sub push to Cloud Run"
fi

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')"
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding "${PUSH_SA}" \
  --project="${PROJECT}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet >/dev/null || true

gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role="roles/datastore.user" \
  --quiet >/dev/null || true
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role="roles/pubsub.publisher" \
  --quiet >/dev/null || true
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role="roles/storage.objectAdmin" \
  --quiet >/dev/null || true
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA}" \
  --role="roles/modelarmor.user" \
  --quiet >/dev/null || true

echo "==> Push subscription (needs FLOCK_WORKER_URL after first worker deploy)"
if [[ -n "${WORKER_URL}" ]]; then
  ENDPOINT="${WORKER_URL%/}/internal/pubsub/campaign-steps"
  if gcloud pubsub subscriptions describe "${SUB}" --project="${PROJECT}" >/dev/null 2>&1; then
    gcloud pubsub subscriptions update "${SUB}" \
      --project="${PROJECT}" \
      --push-endpoint="${ENDPOINT}" \
      --push-auth-service-account="${PUSH_SA}" \
      --ack-deadline=60 \
      --dead-letter-topic="${DLQ}" \
      --max-delivery-attempts=5
  else
    gcloud pubsub subscriptions create "${SUB}" \
      --project="${PROJECT}" \
      --topic="${TOPIC}" \
      --push-endpoint="${ENDPOINT}" \
      --push-auth-service-account="${PUSH_SA}" \
      --ack-deadline=60 \
      --dead-letter-topic="${DLQ}" \
      --max-delivery-attempts=5
  fi
else
  echo "    skip subscription — set FLOCK_WORKER_URL and re-run"
fi

OUT="${ROOT}/infra/runtime.json"
mkdir -p "${ROOT}/infra"
python3 - <<PY
import json, os
path = os.environ.get("OUT", "${OUT}")
doc = {
  "project": "${PROJECT}",
  "region": "${REGION}",
  "vertexRuntimeRegion": "${RUNTIME_REGION}",
  "serviceAccount": "${SA}",
  "pubsubPushServiceAccount": "${PUSH_SA}",
  "topics": {
    "campaignSteps": "${TOPIC}",
    "campaignStepsDlq": "${DLQ}",
    "founderAlerts": "${ALERTS}",
  },
  "subscription": "${SUB}",
  "buckets": {"media": "${MEDIA_BUCKET}", "logs": "${LOGS_BUCKET}"},
  "modelArmor": {"location": "${REGION}", "template": "${ARMOR_TEMPLATE}"},
  "firestoreDatabase": "(default)",
  "cloudRun": {"api": "flock-api", "worker": "flock-worker"},
}
open(path, "w").write(json.dumps(doc, indent=2) + "\n")
print("wrote", path)
PY

echo "==> Done. Next: deploy flock-api + flock-worker, then re-run with FLOCK_WORKER_URL."

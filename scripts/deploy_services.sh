#!/usr/bin/env bash
# Build one image, deploy flock-api (public) and flock-worker (OIDC-only).
set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-leadsy-flock}"
REGION="${GCP_REGION:-asia-south1}"
SA="${GCP_SERVICE_ACCOUNT:-leadsy-agent@${PROJECT}.iam.gserviceaccount.com}"
PUSH_SA="leadsy-pubsub-push@${PROJECT}.iam.gserviceaccount.com"
AR_REPO="${AR_REPO:-cloud-run-source-deploy}"
TAG="${IMAGE_TAG:-$(git -C "$(dirname "${BASH_SOURCE[0]}")/.." rev-parse --short HEAD 2>/dev/null || echo latest)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${AR_REPO}/flock:${TAG}"
MEDIA_BUCKET="${MEDIA_BUCKET_NAME:-${PROJECT}-media-${REGION}}"
LOGS_BUCKET="${LOGS_BUCKET_NAME:-${PROJECT}-logs-${REGION}}"
MEMORY_BANK_ID="${MEMORY_BANK_ID:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PATH="${HOME}/.local/bin:/tmp/google-cloud-sdk/bin:${PATH}"
gcloud config set project "${PROJECT}" >/dev/null
cd "${ROOT}"

COMMON_ENV=$(cat <<EOF
GOOGLE_CLOUD_PROJECT=${PROJECT}
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=true
GCP_REGION=${REGION}
CAMPAIGN_STEPS_TOPIC=campaign-steps
CAMPAIGN_STEPS_DLQ_TOPIC=campaign-steps-dlq
FOUNDER_ALERTS_TOPIC=founder-alerts
MEDIA_BUCKET_NAME=${MEDIA_BUCKET}
LOGS_BUCKET_NAME=${LOGS_BUCKET}
MODEL_ARMOR_LOCATION=${REGION}
MODEL_ARMOR_TEMPLATE=leadsy-inbound
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT
EOF
)
if [[ -n "${MEMORY_BANK_ID}" ]]; then
  COMMON_ENV="${COMMON_ENV}
MEMORY_BANK_ID=${MEMORY_BANK_ID}
MEMORY_BANK_LOCATION=${MEMORY_BANK_LOCATION:-us-central1}"
fi
COMMON_ENV=$(echo "${COMMON_ENV}" | paste -sd, -)

echo "==> Build ${IMAGE}"
gcloud builds submit --project="${PROJECT}" --tag="${IMAGE}" .

echo "==> Deploy flock-api"
gcloud run deploy flock-api \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${SA}" \
  --allow-unauthenticated \
  --timeout=300 \
  --cpu=1 \
  --memory=1Gi \
  --set-env-vars="${COMMON_ENV},OTEL_SERVICE_NAME=flock-api"

echo "==> Deploy flock-worker"
gcloud run deploy flock-worker \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${SA}" \
  --no-allow-unauthenticated \
  --timeout=300 \
  --cpu=1 \
  --memory=1Gi \
  --set-env-vars="${COMMON_ENV},OTEL_SERVICE_NAME=flock-worker"

WORKER_URL="$(gcloud run services describe flock-worker --project="${PROJECT}" --region="${REGION}" --format='value(status.url)')"
echo "==> Grant Pub/Sub push invoker on flock-worker"
gcloud run services add-iam-policy-binding flock-worker \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --member="serviceAccount:${PUSH_SA}" \
  --role="roles/run.invoker" \
  --quiet >/dev/null

echo "==> Attach push subscription"
FLOCK_WORKER_URL="${WORKER_URL}" bash "${ROOT}/scripts/provision_infra.sh"

API_URL="$(gcloud run services describe flock-api --project="${PROJECT}" --region="${REGION}" --format='value(status.url)')"
echo "flock-api    ${API_URL}"
echo "flock-worker ${WORKER_URL}"

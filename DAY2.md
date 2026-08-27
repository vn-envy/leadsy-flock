# Day 2 — Google Cloud runtime

Exit criterion from the locked plan: *one brief flows message → plan → approved → async run skeleton; every step a Firestore receipt AND a trace span; Flock visible in Agent Registry.*

## What this day provisions

| Resource | Name | Region |
|---|---|---|
| Cloud Run API | `flock-api` (unauthenticated demo) | asia-south1 |
| Cloud Run worker | `flock-worker` (OIDC from Pub/Sub only) | asia-south1 |
| Pub/Sub topics | `campaign-steps`, `campaign-steps-dlq`, `founder-alerts` | global |
| Push subscription | `campaign-steps-worker` → `/internal/pubsub/campaign-steps` | |
| Firestore | `(default)` | asia-south1 |
| GCS | `leadsy-flock-media-asia-south1`, `leadsy-flock-logs-asia-south1` | asia-south1 |
| Model Armor | template `leadsy-inbound` (RAI + PI/jailbreak; no malicious-URI — unsupported here) | asia-south1 |
| Service accounts | `leadsy-agent` (run), `leadsy-pubsub-push` (push auth) | |

The worker image is the same as the API. `K_SERVICE` is injected by Cloud Run; the Pub/Sub route 404s on `flock-api`.

Pipeline (Bri v1, catalog-backed, no LLM): `scout → inka → creative_gate → stella → ad_kit` (plus `outreach_gate` when Ray is hired). Day-2 engines write typed stub artifacts; live Scout/Inka/Gemma land next.

## Commands

```bash
export GCP_PROJECT_ID=leadsy-flock
export GCP_REGION=asia-south1
bash scripts/provision_infra.sh
bash scripts/deploy_services.sh
python3 scripts/register_runtime.py
FLOCK_API_URL=https://flock-api-XXXX.asia-south1.run.app bash scripts/e2e_infra.sh
```

## Honest residuals

- **Memory Bank** lives on Vertex Agent Engine. That product is not guaranteed in asia-south1; the registrar tries `us-central1` then records the error in `infra/runtime-extras.json`.
- **Agent Registry** may require a Gemini Enterprise app. Same file records the attempt.
- **Lyria-002** still 429-quota from day 1. Not an infra blocker.
- Worker steps are skeleton receipts until Scout/Inka/Gemma are implemented.

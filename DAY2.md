# Day 2 — Google Cloud runtime

Exit criterion from the locked plan: *one brief flows message → plan → approved → async run skeleton; every step a Firestore receipt AND a trace span; Flock visible in Agent Registry.*

**Met on 27 Aug 2026.** Proof: `proof/infra/e2e-campaign.json`.

## Live services

| Resource | Value |
|---|---|
| flock-api | https://flock-api-533880600838.asia-south1.run.app |
| flock-worker | https://flock-worker-533880600838.asia-south1.run.app |
| Flo chat | `POST /run_sse` (`gemini-3.5-flash`) |
| Campaign API | `POST /v1/campaigns` → `POST /v1/campaigns/{id}/approve` → `GET /v1/campaigns/{id}` |
| Inventory | `GET /v1/infra` |
| Model Armor screen | `POST /v1/screen` |
| A2A card | `/a2a/app/.well-known/agent-card.json` |

## What this day provisioned

| Resource | Name | Region |
|---|---|---|
| Cloud Run API | `flock-api` (unauthenticated demo) | asia-south1 |
| Cloud Run worker | `flock-worker` (Pub/Sub OIDC as `leadsy-pubsub-push`) | asia-south1 |
| Pub/Sub topics | `campaign-steps`, `campaign-steps-dlq`, `founder-alerts` | global |
| Push subscription | `campaign-steps-worker` → `/internal/pubsub/campaign-steps` | |
| Firestore | `(default)` receipts + campaigns | asia-south1 |
| GCS | `leadsy-flock-media-asia-south1`, `leadsy-flock-logs-asia-south1` | asia-south1 |
| Model Armor | template `leadsy-inbound` (RAI + PI/jailbreak; no malicious-URI) | **us-central1** |
| Memory Bank | Vertex Agent Engine `6581665058995044352` | us-central1 |
| Agent Registry | service `leadsy-flock` / agent `Leadsy Flock (Flo)` | us-central1 |
| Service accounts | `leadsy-agent` (run), `leadsy-pubsub-push` (push auth) | |

The worker image is the same as the API. `K_SERVICE` is injected by Cloud Run; the Pub/Sub route 404s on `flock-api`.

Pipeline (Bri v1, catalog-backed, no LLM): `scout → inka → creative_gate → stella → ad_kit` (plus `outreach_gate` when Ray is hired). Day-2 engines write typed stub artifacts; live Scout/Inka/Gemma land next.

Verified campaign `peak-gym-1f7d7f56`: receipts `plan`, `approve`, `scout`, `inka`, `creative_gate`, `stella`, `ad_kit` all `ok`, campaign `status=completed`.

## Commands

```bash
export GCP_PROJECT_ID=leadsy-flock
export GCP_REGION=asia-south1
bash scripts/provision_infra.sh
bash scripts/deploy_services.sh
python3 scripts/register_runtime.py
FLOCK_API_URL=https://flock-api-533880600838.asia-south1.run.app bash scripts/e2e_infra.sh
```

## Honest residuals

- **Model Armor writes are denied in asia-south1** even for the Editor SA. The live template is in **us-central1**. Inbound screening uses that regional endpoint and succeeds (`NO_MATCH_FOUND` on a gym brief).
- **Project `setIamPolicy` is denied** for `leadsy-agent`. Extra project roles (e.g. `modelarmor.admin`) cannot be self-granted. Editor + `run.admin` was enough for topics, buckets, Cloud Run, Firestore, and the push subscription. Token-creator on the push SA could not be bound; OIDC push still delivered (Pub/Sub created the subscription and the worker processed the pipeline).
- **Agent card `url`** is the public Cloud Run URL when `APP_URL` is set on the revision (now set).
- **Worker steps are skeleton receipts** until Scout/Inka/Gemma are implemented.
- **Lyria-002** still 429-quota from day 1. Not an infra blocker.
- Model Armor template currently records hate-speech + PI/jailbreak + CSAM; harassment/sexual/dangerous RAI flags may need a template update if the CLI dropped them on create.

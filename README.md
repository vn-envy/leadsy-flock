# Leadsy Flock

**An AI growth agency for small businesses, rebuilt on Gemini + ADK + Google Cloud.**

One chat message in. A researched, gated, consented campaign out. Every action on the record.

> **Hackathon entry** — Google All Things Agentic, 27–31 August 2026.
> Concept lineage: an earlier prototype on a different stack. **This repo is a ground-up rebuild.** See [DISCLOSURE.md](DISCLOSURE.md).

## Status (27 Aug 2026)

Hello Flo is live. The flock engines run on Pub/Sub + Cloud Run:

- **API:** https://flock-api-533880600838.asia-south1.run.app — Flo (`gemini-3.5-flash`) + `/v1/campaigns`
- **Worker:** https://flock-worker-533880600838.asia-south1.run.app — Scout → Inka → Creative Gate → Stella → Ad Kit
- `GET /health` — liveness (`/healthz` is intercepted by Cloud Run's frontend)
- `GET /v1/infra` — runtime inventory (Firestore, topics, Model Armor, Memory Bank)
- `GET /console` — receipts Mission Control
- `GET /demo` — clocked judge script (fictional Mira's Chai)
- `GET /s/{campaignId}?k=` — owner studio (delivery room, UTM hits, quoted vs production band)
- `GET /ops` — founder quoted vs burn (`OPS_TOKEN`)
- `GET /l/{campaignId}` — Stella consent-first landing with still; clip/jingle unhide when harvest finishes; `utm_*` query records a hit
- `GET /k/{campaignId}` — agency paste kit (own-shop frames when we have them, 8s Veo, English + Indic VO, UTMs, no autopost)
- `POST /v1/telegram/webhook` — same ADK Flo as `/run_sse` when `TELEGRAM_BOT_TOKEN` is set
- `GET /media/{campaignId}/still` — Gemini 3.1 Flash Image (Imagen 3 successor)
- `GET /media/{campaignId}/{slot}` — `still-*` crops, Veo `clip` / `clip-captioned` / `clip-story` / …, Lyria `jingle` once harvest writes GCS
- `POST /v1/consents` — Model Armor on the way in
- Notes: [DAY1.md](DAY1.md) · [DAY2.md](DAY2.md) · [DAY3.md](DAY3.md) · [DAY4.md](DAY4.md) · [design.md](design.md)

## Mandatory stack

| Requirement | This project |
|---|---|
| Gemini 3.5+ | `gemini-3.5-flash` (Flo) via Vertex AI, global endpoint |
| Google agent framework | ADK 2.x, scaffolded with `agents-cli` (`adk` template, A2A built in) |
| Google Cloud service | Cloud Run (`flock-api` + `flock-worker`, `asia-south1`) + Firestore + Pub/Sub + Model Armor + Cloud Trace |

Veo 3.1 starts in Inka and is harvested by the `inka_harvest` sidecar so the flock never waits on a long-running op. Lyria retries on that sidecar (often 429 on this project's quota). Gemma is still the Creative Gate classifier.

## Spin-up

```bash
# Tooling
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install "google-agents-cli~=1.4.1"

# GCP — Vertex AI user or the leadsy-agent service account
gcloud auth application-default login   # or GOOGLE_APPLICATION_CREDENTIALS
gcloud config set project YOUR_GCP_PROJECT
cp .env.example .env                    # set GOOGLE_CLOUD_PROJECT

# Run
agents-cli install
agents-cli run "Hi Flo — I run a gym in Gurgaon and need 50 new members."
```

Deploy runtime (Cloud Build; no local Docker required):

```bash
bash scripts/provision_infra.sh
bash scripts/deploy_services.sh
```

Talk to the deployed service:

```bash
# health
curl https://flock-api-<hash>.asia-south1.run.app/health

# Flo
USER=judge
curl -sS -X POST https://flock-api-<hash>.asia-south1.run.app/apps/app/users/$USER/sessions \
  -H 'content-type: application/json' -d '{"state":{}}'
# then POST /run_sse with app_name=app, user_id, session_id, new_message
```

## Layout

```
app/                 Flo (ADK) + FastAPI + ledger + worker + A2A + OTel
web/                 Mission Control starter (Next.js)
scripts/             provision, deploy, registry, Veo/Lyria smoke
infra/               Terraform mirror + runtime.json
deployment/          agents-cli Terraform (scaffold)
tests/               unit + integration + eval datasets
DISCLOSURE.md        pre-existing work statement
```

## Category

Built for **Fortified Enterprise Fleet** (AgentCards, gates, traces, Memory Bank next).
Falls back to **Taskmaster** if the governance surface slips.

Apache-2.0. Scaffolding © Google LLC.

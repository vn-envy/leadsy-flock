# Day 3 — Engines that actually run

Exit criterion: *Scout grounds on Maps/Search, Inka produces multimodal assets, the Creative Gate can reject a claim, Stella publishes a consent-first page, Ad Kit fans out without autoposting.*

## What runs now

| Step | Engine | What it does |
|---|---|---|
| `scout` | Gemini 3.5 Flash + Maps + Search + urlContext | `evidence[]`, `brandSpec`, local + crowd insight |
| `inka` | Gemini copy · `gemini-2.5-flash-image` · Veo 3.1 · Lyria-002 | copy + GCS assets (Lyria may 429) |
| `creative_gate` | Gemma classifier + Gemini judge + regex | fail-closed; writes policy memory; one Inka revision |
| `stella` | template | `GET /l/{campaignId}` with required consent checkbox |
| `ad_kit` | Inka-Adapt | Meta 1:1 / 9:16 + Google RSA, UTM, `autopost: false` |
| `outreach_gate` / `ray` | Ledge / Ray | refuse without consent; sandbox outbox only |

Judge surfaces:

- https://flock-api-533880600838.asia-south1.run.app/console
- `GET /l/{id}` after Stella
- `POST /v1/consents` (Model Armor on the way in)
- Telegram webhook `POST /v1/telegram/webhook` when `TELEGRAM_BOT_TOKEN` is set

## Honest residuals

- Stagehand / Browserbase is not in this hop (no key). Maps + Search + urlContext still carry Scout.
- last30days engine not vendored; crowd insight is Gemini Search-grounded, not the MIT scraper.
- **Worker Inka skips Veo and Lyria by default** (`INKA_SKIP_VEO=1`, `INKA_SKIP_LYRIA=1`). Waiting on Veo LROs blew the Cloud Run 540s budget and stampeded Pub/Sub. Veo/Lyria remain proven via `scripts/smoke_models.py`; the worker still generates a Gemini still + copy, and records skip receipts for clip/jingle.
- Vertex clients are process-cached. Ephemeral `genai.Client()` objects in google-genai 2.x raise `Cannot send a request, as the client has been closed` before Inka/Gemma/the judge can run.
- Gemma `gemma-3-12b-it` 404s as a publisher model on this project's `us-central1` Vertex. Regex + Gemini 3.5 Flash judge still fail-closed (proven on `peak-gym-71d02b5c`).
- Remotion derivatives and zip/paste-guide are day-4 surface area; this kit is copy + dimensions + UTMs + GCS masters.
- Telegram webhook is wired (`POST /v1/telegram/webhook`) but inactive until `TELEGRAM_BOT_TOKEN` is set on Cloud Run.

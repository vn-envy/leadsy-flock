# Day 3 — Engines that actually run

Exit criterion: *Scout grounds on Maps/Search, Inka produces multimodal assets, the Creative Gate can reject a claim, Stella publishes a consent-first page, Ad Kit fans out without autoposting.*

## What runs now

| Step | Engine | What it does |
|---|---|---|
| `scout` | Gemini 3.5 Flash + Maps + Search + urlContext | `evidence[]`, `brandSpec`, local + crowd insight |
| `inka` | Gemini copy · `gemini-3.1-flash-image` still · Veo **start only** | copy + GCS still; Veo LRO name on the receipt — no wait |
| `creative_gate` | Gemma classifier + Gemini judge + regex | fail-closed; writes policy memory; one Inka revision |
| `stella` | template | `GET /l/{campaignId}` with required consent checkbox |
| `ad_kit` | Inka-Adapt | Meta 1:1 / 9:16 + Google RSA, UTM, `autopost: false` |
| `inka_harvest` | sidecar (not in the sequential pipeline) | poll Veo once per invocation; retry Lyria twice; republish until GCS or max attempts |
| `outreach_gate` / `ray` | Ledge / Ray | refuse without consent; sandbox outbox only |

Judge surfaces:

- https://flock-api-533880600838.asia-south1.run.app/console
- `GET /l/{id}` after Stella
- `POST /v1/consents` (Model Armor on the way in)
- Telegram webhook `POST /v1/telegram/webhook` when `TELEGRAM_BOT_TOKEN` is set

## Honest residuals

- Stagehand / Browserbase is not in this hop (no key). Maps + Search + urlContext still carry Scout.
- last30days engine not vendored; crowd insight is Gemini Search-grounded, not the MIT scraper.
- **Veo wait-in-Inka was the timeout bug, not Veo itself.** Inka now *starts* the Veo LRO (seconds) and returns. A sidecar step `inka_harvest` polls `operations.get` once per worker invocation, sleeps `HARVEST_POLL_SECONDS` (12), and republishes itself (max 16). It never `publish_next`s and never marks the campaign `completed`. Stella always emits `/media/{id}/clip` and `/jingle`; the page polls `GET /media/{id}/ready` until harvest writes GCS.
- **Lyria stays off the Inka hot path.** Harvest tries Lyria on attempts 1–2; after attempt ≥ 3 without GCS it records a quota skip so a 429 cannot stall Scout→Ad Kit. `INKA_SKIP_VEO=1` / `INKA_SKIP_LYRIA=1` remain available.
- **Imagen 3 is gone.** Vertex discontinued `imagen-3.0-generate-002` (and the rest of the Imagen 3/4 publisher IDs) on 30 Jun 2026. This project 404s those IDs in `us-central1` and `global`. Google's replacement is Gemini image: `gemini-3.1-flash-image` on **global** (fallback `gemini-2.5-flash-image` on us-central1). Stills land in GCS and are served at `GET /media/{id}/still` on the Stella page.
- Vertex clients are process-cached. Ephemeral `genai.Client()` objects in google-genai 2.x raise `Cannot send a request, as the client has been closed` before Inka/Gemma/the judge can run.
- Gemma `gemma-3-12b-it` 404s as a publisher model on this project's `us-central1` Vertex. Regex + Gemini 3.5 Flash judge still fail-closed (proven on `peak-gym-71d02b5c`).
- Remotion derivatives and zip/paste-guide are day-4 surface area; this kit is copy + dimensions + UTMs + GCS masters.
- Stella landings use locked tokens from [design.md](design.md). Scout names a `themeId`; orange brand paint cannot become the page background.

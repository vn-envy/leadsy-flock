# Day 4 — Meeting, delivery room, founder ops

Exit criterion: *Telegram talks to the same ADK Flo as `/run_sse`. The owner gets a studio URL when the kit is ready. Founder `/ops` shows quoted vs burn. Judges can clock a fictional brief. No autopost. No outreach to a real shop.*

## Surfaces

| Who | URL | Auth |
|---|---|---|
| Owner meeting | Telegram DM → `POST /v1/telegram/webhook` | Bot token + `X-Telegram-Bot-Api-Secret-Token` |
| Owner delivery | `GET /s/{id}?k=` | `studioKey` query |
| Paste kit | `GET /k/{id}` | public (same as before) |
| Consent + UTM | `GET /l/{id}?utm_*` | public; `utm_*` writes `landing_hit` |
| Founder | `GET /ops?token=` | `OPS_TOKEN` |
| Judges | `GET /demo` | public, fictional Mira's Chai |
| Receipts | `GET /console` | public Mission Control |

## Telegram (you configure)

1. BotFather `/newbot`. Copy the token — never commit it.
2. Optional: `/setjoingroups` disable. Flo is **DM only**.
3. After flock-api is deployed with this hop:

```bash
gcloud run services update flock-api --project=leadsy-flock --region=asia-south1 \
  --update-env-vars="TELEGRAM_BOT_TOKEN=...,TELEGRAM_WEBHOOK_SECRET=...,TELEGRAM_ALLOW_USER_IDS=your_numeric_id,OPS_TOKEN=..."

curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://flock-api-533880600838.asia-south1.run.app/v1/telegram/webhook" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}" \
  -d "allowed_updates=[\"message\"]"
```

Commands in chat: `/start` · brief · `YES` / `/approve` · `/status`.

`--update-env-vars` keeps other Cloud Run env (do not `--set-env-vars` or you wipe Vertex).

## Clocked judge script

1. Open `/demo` and a stopwatch.
2. Paste the Mira's Chai brief into Telegram (or Flo on the API).
3. YES. Do not wait for a Friday email — the kit URL is stable.
4. Second device: studio from the kit-ready ping.
5. Click a kit UTM. Studio hit count moves. That is “run ads” without autopost.
6. Founder tablet: `/ops?token=` quoted vs list-price burn (Veo is ~90% of COGS).

Use a shop you own or this fictional stall. Do not cold-contact Glen's Bakehouse or any live listing.

## Cost honesty

Receipts now carry Flash token usage when Vertex returns `usage_metadata`. Veo/TTS/Lyria are inferred from harvested assets at list price ($0.40/s Veo + audio). `/ops` is **not** a Google invoice.

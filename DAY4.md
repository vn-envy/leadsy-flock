# Day 4 — Meeting, delivery room, founder ops

Exit criterion: *The capture form is the meeting. YES on `/r/{id}?k=` starts the flock. The same URL becomes the delivery room when the kit is ready. Founder `/ops` shows quoted vs burn. Judges can clock a fictional brief. No autopost. No outreach to a real shop. Telegram is off the hackathon door.*

## Surfaces

| Who | URL | Auth |
|---|---|---|
| Owner meeting | `GET /` — paste website or Google listing | public |
| Owner run | `GET /r/{id}?k=` — quote, YES, tracker, studio | `studioKey` query |
| Owner delivery | `GET /s/{id}?k=` | `studioKey` query |
| Paste kit | `GET /k/{id}` | public (same as before) |
| Consent + UTM | `GET /l/{id}?utm_*` | public; `utm_*` writes `landing_hit` |
| Founder | `GET /ops?token=` | `OPS_TOKEN` |
| Judges | `GET /demo` | public, fictional Mira's Chai; prefill `/?name=&geo=&goal=` |
| Receipts | `GET /console` | public Mission Control |

Telegram (`POST /v1/telegram/webhook`) stays in the codebase and returns 501 without a bot token. It is **not** the event door. Pulse / OpenSEO is parked in [PULSE.md](PULSE.md).

## Clocked judge script

1. Open `/demo` and a stopwatch.
2. Follow the prefilled form on `/`. Paste a listing or website **you own** (Mira's stall has none). Any public shop URL works for the clock.
3. YES. Do not wait for a Friday email — the run URL is stable.
4. Watch Scout → Inka → Gate → Stella → Ad Kit. Studio iframe opens on the same page.
5. Click a kit UTM. Studio hit count moves. That is “run ads” without autopost.
6. Founder tablet: `/ops?token=` quoted vs list-price burn (Veo is ~90% of COGS).

Use a shop you own or this fictional stall plus a URL you control. Do not cold-contact Glen's Bakehouse or any live listing.

## Parked (after the hackathon)

[PULSE.md](PULSE.md) — OpenSEO market intel sidecar. Approved, not in this event build.

Telegram DM Flo — code remains; not the product path for the event.

## Cost honesty

Receipts now carry Flash token usage when Vertex returns `usage_metadata`. Veo/TTS/Lyria are inferred from harvested assets at list price ($0.40/s Veo + audio). `/ops` is **not** a Google invoice.

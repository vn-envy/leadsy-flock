# Day 4 — Meeting, delivery room, founder ops

Exit criterion: *The capture form is the meeting. YES on `/r/{id}?k=` starts the flock. The same URL becomes the delivery room when the kit is ready. Founder `/ops` shows quoted vs burn. Judges open the seeded Glen's Bakehouse kit. No autopost. No outreach to a real shop. Telegram is off the hackathon door.*

## Surfaces

| Who | URL | Auth |
|---|---|---|
| Owner meeting | `GET /` — paste website or Google listing | public |
| Owner run | `GET /r/{id}?k=` — quote, YES, tracker, studio | `studioKey` query |
| Owner delivery | `GET /s/{id}?k=` | `studioKey` query |
| Paste kit | `GET /k/{id}` | public (same as before) |
| Consent + UTM | `GET /l/{id}?utm_*` | public; `utm_*` writes `landing_hit` |
| Founder | `GET /ops?token=` | `OPS_TOKEN` |
| Judges | `GET /demo` | public, seeded Glen's Bakehouse kit `google-listing-eaf57cae` |
| Receipts | `GET /console` | public Mission Control |

Telegram (`POST /v1/telegram/webhook`) stays in the codebase and returns 501 without a bot token. It is **not** the event door. Pulse / OpenSEO is parked in [PULSE.md](PULSE.md).

## Seeded judge script

The final demo is the **already-finished** Glen's Bakehouse campaign (`google-listing-eaf57cae`), not a fictional stall and not a second YES on this listing.

1. Open `/demo`. Kit, still, place film, proof film, English + Hindi 9:16 are on the page.
2. Open `/k/google-listing-eaf57cae`. Paste RSA / UTMs. Own bakery photos, not an invented shop.
3. Second device: landing UTM on `/l/google-listing-eaf57cae?utm_source=meta&utm_content=meta_feed`. Consent is still a checkbox. That is “run ads” without autopost.
4. Capture form at `/` can show the same listing prefilled so judges see the door. If you want a fresh YES, paste a shop **you own**.
5. Founder tablet: `/ops?token=` quoted vs list-price burn (Veo is ~90% of COGS).

Public listing used as a pipeline proof: `https://share.google/rLF34cfolz9TJA92F`. Do not email, call, review, or autopost.

## Parked (after the hackathon)

[PULSE.md](PULSE.md) — OpenSEO market intel sidecar. Approved, not in this event build.

Telegram DM Flo — code remains; not the product path for the event.

## Cost honesty

Receipts now carry Flash token usage when Vertex returns `usage_metadata`. Veo/TTS/Lyria are inferred from harvested assets at list price ($0.40/s Veo + audio). `/ops` is **not** a Google invoice.

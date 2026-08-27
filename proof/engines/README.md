# Engine E2E proof

Live campaign **`peak-gym-71d02b5c`** on 27 Aug 2026.

- API: https://flock-api-533880600838.asia-south1.run.app
- Console: https://flock-api-533880600838.asia-south1.run.app/console
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/peak-gym-71d02b5c

| Step | Result |
|---|---|
| Scout | Maps + Search grounding URIs, BrandSpec, local/crowd insight |
| Inka | Gemini copy + `gemini-2.5-flash-image` still in GCS (~1.3MB). Veo/Lyria skipped in-worker |
| Creative Gate | Draft `guaranteed` **rejected**; final headline **pass**; Gemini judge `ok` |
| Stella | Consent-first HTML at `/l/{id}` |
| Ad Kit | Meta 1:1 / 9:16 + Google RSA, `autopost: false` |
| Consent | `POST /v1/consents` stored (Armor allowed) |

Gemma `gemma-3-12b-it` 404s on this project's us-central1 publisher models. Regex + Gemini judge still fail-closed.

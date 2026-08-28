# Engine E2E proof

Live campaign **`peak-gym-05636371`** on 28 Aug 2026 (Veo harvest sidecar).

- API: https://flock-api-533880600838.asia-south1.run.app
- Console: https://flock-api-533880600838.asia-south1.run.app/console
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/peak-gym-05636371
- Still: https://flock-api-533880600838.asia-south1.run.app/media/peak-gym-05636371/still
- Clip: https://flock-api-533880600838.asia-south1.run.app/media/peak-gym-05636371/clip
- Ready: https://flock-api-533880600838.asia-south1.run.app/media/peak-gym-05636371/ready

| Step | Result |
|---|---|
| Scout | Maps + Search grounding URIs, BrandSpec |
| Inka | Gemini copy + **`gemini-3.1-flash-image`** still (1.6MB PNG). Veo LRO **started only** (1.7s) |
| Creative Gate | Draft `guaranteed` **rejected**; final headline **pass** |
| Stella | Consent-first HTML with still; clip/jingle hooks; polls `/media/{id}/ready` |
| Ad Kit | Meta 1:1 / 9:16 + Google RSA, `autopost: false` |
| `inka_harvest` | Attempt 6 **ok**. Veo `veo-3.1-generate-001` **1.39MB mp4** in GCS. Lyria-002 **429 skipped** (quota), flock still completed |

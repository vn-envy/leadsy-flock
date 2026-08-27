# Engine E2E proof

Live campaign **`peak-gym-a49dae31`** on 27 Aug 2026 (visuals hooked).

- API: https://flock-api-533880600838.asia-south1.run.app
- Console: https://flock-api-533880600838.asia-south1.run.app/console
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/peak-gym-a49dae31
- Still: https://flock-api-533880600838.asia-south1.run.app/media/peak-gym-a49dae31/still

| Step | Result |
|---|---|
| Scout | Maps + Search grounding URIs, BrandSpec |
| Inka | Gemini copy + **`gemini-3.1-flash-image`** still (1.4MB PNG). Imagen 3 publisher IDs 404 after 30 Jun 2026. Veo/Lyria skipped in-worker |
| Creative Gate | Draft `guaranteed` **rejected**; final headline **pass** |
| Stella | Consent-first HTML with hero `<img src="/media/{id}/still">` |
| Ad Kit | Meta 1:1 / 9:16 + Google RSA, `autopost: false` |

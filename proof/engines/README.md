# Engine E2E proof

## Peak Gym (Veo harvest)

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

## Noya Salon (asset kit)

Fictional salon on Golf Course Road, same geo, **28 Aug 2026**. Campaign **`noya-salon-7384033d`**. Theme **`paper`**.

- Kit: https://flock-api-533880600838.asia-south1.run.app/k/noya-salon-7384033d
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/noya-salon-7384033d
- Console: https://flock-api-533880600838.asia-south1.run.app/console
- Ready: https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-7384033d/ready

| Slot | Bytes | Notes |
|---|---|---|
| still 16:9 | 1.48MB | Gemini master, Stella hero |
| still-story 9:16 | 1.88MB | Gemini vertical master |
| still-feed 4:5 | 1.43MB | crop |
| still-square 1:1 | 1.32MB | crop |
| still-landscape 1.91:1 | 2.30MB | crop |
| clip 16:9 | 1.57MB | Veo `veo-3.1-generate-001`, harvest attempt 4 |
| clip-story / feed / square / landscape | 512–667KB | ffmpeg centre crops from the Veo master |
| jingle | missing | Lyria-002 quota skip; flock still completed |

Ad Kit paste page lists Meta feed 4:5, square, Reels 9:16, WhatsApp status, Google display 1.91:1, Google RSA. `autopost: false`. Creative Gate rejected the draft claim and passed the final headline. Consent recorded from the landing. No real salon was contacted.

## Noya Salon (shelf short + Indic locale)

Fictional salon, same brief, **28 Aug 2026**. Campaign **`noya-salon-fff1d666`**. Theme **`paper`**. Locale **`hi-IN`**.

- Kit: https://flock-api-533880600838.asia-south1.run.app/k/noya-salon-fff1d666
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/noya-salon-fff1d666
- Console: https://flock-api-533880600838.asia-south1.run.app/console
- Ready: https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-fff1d666/ready
- Captioned 9:16: https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-fff1d666/clip-captioned

| Check | Result |
|---|---|
| Scout shelf | 3 http URIs (Looks Salon, L'Oréal Professionnel, Godrej Professional) — structure only |
| Locale | `hi-IN` / Devanagari. `voIndic` on the kit. Brand name stays Latin |
| Inka Veo start | 8s, `9:16`, `generateAudio: true`, 3 ASSET refs |
| Harvest | Attempt 11. First LRO RAI-filtered people/face; fallback **9:16 no refs**. `clip.mp4` 1.68MB, **720×1280, 8.0s, h264+aac** |
| Captions | `clip-captioned.mp4` 916KB with `NotoSansDevanagari-Regular.ttf`. Crops kept AAC |
| Gate | Draft rejected; final **pass**. EN + Indic scanned |
| Kit | Story hook + spoken line + shelf links. Reels/WhatsApp use `clip-captioned`. `autopost: false` |
| Jingle | Lyria-002 **429 skipped**; flock still completed |

Does not overwrite `noya-salon-7384033d`. No real salon was contacted.

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

## Noya Salon (own photos → Veo + dual VO)

Fictional salon, same brief, **28 Aug 2026**. Campaign **`noya-salon-e548bd87`**. Theme **`paper`**. Locale **`hi-IN`**.

Owner frames were the previous campaign's stills, passed as `assetUris` (stand-in for website / listing / menu / shop photos). Gemini did **not** invent a shop. Image refine hit **429**, so Inka kept the raw owner frames. Those three frames went to Veo as ASSET refs.

- Kit: https://flock-api-533880600838.asia-south1.run.app/k/noya-salon-e548bd87
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/noya-salon-e548bd87
- English film: https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-e548bd87/clip-en
- Hindi film: https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-e548bd87/clip-indic
- Captioned 9:16 (Hindi): https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-e548bd87/clip-captioned
- Captioned 9:16 (English): https://flock-api-533880600838.asia-south1.run.app/media/noya-salon-e548bd87/clip-captioned-en

| Check | Result |
|---|---|
| Origin | **`own`**, `ownCount` 3. Stills `still` / `still-story` / `still-detail` are owner photos |
| Refine | Gemini image-to-image **429**; raw owner bytes kept |
| Inka Veo start | 8s, `9:16`, `generateAudio: true` (room tone only), **`usedRefs: true`** |
| Harvest | Attempt 3. `clip.mp4` 4.63MB. Captions EN + Indic |
| Dual VO | Gemini TTS Kore (EN) + Puck (Hindi), PCM wrapped as WAV, muxed to **`clip-en` 1.70MB** and **`clip-indic` 1.79MB** |
| Kit | Reels/WhatsApp use `clip-indic` + `clip-en`. Copy lists both spoken lines. Lede: own photos. `autopost: false` |
| Jingle | Lyria-002 **429 skipped**; flock still completed |

Does not overwrite `noya-salon-fff1d666` or `noya-salon-7384033d`. No real salon was contacted. Gemini still-from-scratch is only used when the shop has no usable visual evidence.

## Glen's Bakehouse (live Google listing sanity check)

Public listing `https://share.google/rLF34cfolz9TJA92F` on **28 Aug 2026**. Campaign **`google-listing-eaf57cae`**. **Do not contact this business.**

Scout opened the share link (urlContext), resolved **Glen's Bakehouse**, Indiranagar, vertical **food**. `glensbakehouse.com/menu.pdf` 404s; own frames came from the live homepage CSS `background-image` photos (6 frames). Gemini did **not** invent a shop.

- Kit: https://flock-api-533880600838.asia-south1.run.app/k/google-listing-eaf57cae
- Landing: https://flock-api-533880600838.asia-south1.run.app/l/google-listing-eaf57cae
- Place 4:5: https://flock-api-533880600838.asia-south1.run.app/media/google-listing-eaf57cae/clip-feed
- Proof 4:5: https://flock-api-533880600838.asia-south1.run.app/media/google-listing-eaf57cae/clip-proof-feed
- English 9:16: https://flock-api-533880600838.asia-south1.run.app/media/google-listing-eaf57cae/clip-en
- Hindi 9:16: https://flock-api-533880600838.asia-south1.run.app/media/google-listing-eaf57cae/clip-indic

| Check | Result |
|---|---|
| Origin | **`own`**, `ownCount` 6. Stills are bakery photos from glensbakehouse.com |
| Inka Veo | Two 8s 9:16 LROs, `usedRefs: true` (place + proof). Room tone only |
| Channel pixels | `clip-feed` **1080×1350**, square **1080×1080**, story **1080×1920**, landscape **1200×628**. Proof slots match |
| Dual VO | Kore EN + Puck Hindi on both films (`clip-en` / `clip-indic` and `clip-proof-en` / `clip-proof-indic`) |
| Kit | Aspect frames (`data-aspect`), `1080×1350` badges, Save links, place + proof. `autopost: false` |
| Gate | Draft rejected if it overclaimed; final **pass**. Headline names Indiranagar / red velvet |
| Jingle | Lyria skipped on harvest so 429 cannot stall the flock |

Does not overwrite Noya or Peak Gym writeups. No email, call, review, or autopost.

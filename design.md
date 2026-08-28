# Landing design

Stella does not invent CSS colours. Scout may *name* a theme; `app/design.py` is the only place hex becomes a page token. If a BrandSpec palette would fail WCAG AA, it is discarded.

## Rules

1. **Accent is never the page background.** `#FF6B00` on a gym brief is a CTA colour, not a canvas.
2. **Body text sits on `--bg` at ≥ 7:1** (AAA). Muted copy ≥ 4.5:1. Kicker/accent on `--bg` ≥ 3:1 (large UI). CTA label on `--accent` ≥ 4.5:1.
3. **One type pairing everywhere:** Georgia (headline) + `system-ui` (UI). No remote webfonts.
4. **One layout:** dark or light canvas, single column `min(38rem)`, 16:9 hero, consent checkbox required.
5. **Scout output** is `themeId` plus optional accent hex. Raw `palette[]` is for image prompts only.

## Themes

| id | Use when | `--bg` | `--fg` | `--muted` | `--accent` | `--accent-fg` |
|---|---|---|---|---|---|---|
| `inkstone` | default / unknown | `#14181f` | `#f3eee6` | `#b7aea2` | `#c4a574` | `#14181f` |
| `ember` | gyms, energy, warm brands | `#16120f` | `#f6efe8` | `#c4b6a8` | `#e08a4a` | `#16120f` |
| `grove` | wellness, outdoors | `#101510` | `#eaf0e8` | `#a9b5a8` | `#c4b07a` | `#101510` |
| `slate` | professional services | `#10161c` | `#e8eef3` | `#9aa8b4` | `#7eaebe` | `#10161c` |
| `paper` | clinics, cafés, light sites | `#f7f1e8` | `#1c1814` | `#5e574e` | `#8b5a2b` | `#f7f1e8` |

`--surface` is a step off `--bg` for fields. `--line` is a low-contrast hairline. Surfaces are derived in code, not by the model.

## Mapping a BrandSpec

1. If `themeId` is one of the five ids, use that theme.
2. Else look at `palette[]`:
   - bright orange/red (hue 8–45, sat ≥ 0.4) + a dark → `ember`
   - green-dominant → `grove`
   - blue-dominant → `slate`
   - overall light → `paper`
   - otherwise `inkstone`
3. An accent hex from Scout is kept only if it still passes the contrast rules against the chosen `--bg` and as a button fill. Otherwise the theme accent wins.

## Asset kit

A local-agency launch kit is not one landscape still. 2026 Meta + Google delivery is covered by **four ratios**. Copy stays off the raster (no on-screen type) so safe-zone UI cannot cover a headline we burned in.

| Slot | Ratio | Pixels (target) | Where it runs |
|---|---|---|---|
| `still` / `clip` | 16:9 | landing + in-stream | Stella, YouTube/in-stream |
| `still-landscape` / `clip-landscape` | 1.91:1 | 1200×628 class | Google RDA / link ads |
| `still-square` / `clip-square` | 1:1 | 1080×1080 | Carousel, Marketplace, fallback |
| `still-feed` / `clip-feed` | 4:5 | 1080×1350 | Meta/Instagram Feed (default 2026) |
| `still-story` / `clip-story` | 9:16 | 1080×1920 | Stories, Reels, Shorts, WhatsApp status |

Masters: one 16:9 Gemini still, one 9:16 Gemini still, one Veo 16:9 clip (harvested). Derivatives are **centre crops** — Veo prompts keep the subject in the middle third. Theme tokens from this file colour the kit page (`/k/{id}`), never the pixels.

We do **not** ship: IAB GIF banners, logo packs, or a zip. The kit page is the paste guide. **No autopost.**

## Do not

- Paint `body` with the loudest brand colour.
- Put white type on orange, or gold type on bone, without a contrast check.
- Load Inter / Montserrat / gradient meshes on landings.
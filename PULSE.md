# Pulse — parked until after the hackathon

**Status:** approved, not built. Do not implement during All Things Agentic.

Approved 30 Aug 2026: hosted OpenSEO MCP as a **capped `pulse` sidecar** on the ₹5,997 launch bundle. Not a ninth bird. Not Flo-with-MCP. Not a self-hosted OpenSEO.

Upstream: [every-app/open-seo](https://github.com/every-app/open-seo) · MCP `https://app.openseo.so/mcp` · env `OPENSEO_API_KEY` (`oseo_…`).

## Locked decisions

1. **Include Pulse in the launch SKU** (₹5,997). COGS is ~$0.20–$0.80 vs ~$6.40 Veo. Do not sell it as a ₹1,999 Semrush clone.
2. **Hosted OpenSEO API key**, not raw DataForSEO, not self-host (Docker/Cloudflare/Railway).
3. **Scout stays qualitative** (photos, ownUris, shelf tropes). **Pulse stays quantitative** (volume, difficulty, SERP occupants, 3 presence fixes).
4. **Fail-open.** No key, 402/429, or no website+listing → `pulse` receipt `skip`. Kit still ships.
5. **Fixed recipe, not chat tools.** Max 6 MCP calls and ~$0.80/campaign. Never AI-visibility (~$1.09) or full site-audit crawl on this SKU.
6. **No ranking promises, no autopost, no outreach lists.** Public SERP occupants only. Smoke on a listing we own — not a shop we do not operate.

## Pipeline when we build

```
scout → pulse → inka → creative_gate → stella → ad_kit
```

`marketIntel` on the pulse receipt: `keywords[]`, `niches[]`, `serpOccupants[]`, `presence[]` (max 3), `adNarrative`, `sources[]`, `usage`.

Surfaces: Inka prompt block · Ad Kit **Search presence** card · studio table · one Telegram kit-ready line · `/ops` Pulse USD.

## Build hops (say go after the hackathon)

1. `app/engines/openseo.py` — HTTP MCP client + fixtures. No live credits in CI.
2. `app/engines/pulse.py` + worker step. Shape with Flash. Skip if no key.
3. Planner, Inka, Ad Kit, studio, cost SKU, kit-ready sentence.
4. Live smoke on a shop we own. Then `--update-env-vars=OPENSEO_API_KEY=…` on Cloud Run.

**Later, not hop 1:** owner-connected GSC, AI visibility add-on, weekly rank-track retain.

## Do not

- Vendor or fork OpenSEO into this repo.
- Give Flo unconstrained MCP.
- Invent keywords when MCP is down.
- Wipe Cloud Run env with `--set-env-vars` when adding the key.

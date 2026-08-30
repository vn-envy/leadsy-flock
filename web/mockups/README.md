# UI mockups (not production routes)

Open `web/mockups/index.html` in a browser.

| File | What |
|---|---|
| `characters.html` | Eight SVG stamp-birds + idle 2D motion |
| `home.html` | Capture page → Telegram (`t.me/YOUR_BOT` placeholder) |
| `admin.html` | Founder ops (maps to live `/ops`) |
| `studio.html` | Owner delivery room (maps to live `/s/{id}?k=`) |

Raster comps: `proof/ui-mockups/*.png`.

**Do not ship these as the product yet.** Approve motion + layout, then we wire homepage on flock-api, restyle `/ops` and `/s/{id}`, and swap `YOUR_BOT`.

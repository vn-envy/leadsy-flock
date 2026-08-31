# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Generate flamingo-flock art with Vertex Gemini. No people. Run once, commit the PNGs."""

from __future__ import annotations

import json
from pathlib import Path

from google.genai import types

from app.engines import gemini_util as g

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "flock"

PALETTE = (
    "Strict palette only: matte flamingo pink #C9899A, dusty rose #B56E7C, "
    "olive #6A7A55, sage #8A9478, off-white #F3EEE8, warm grey #9A9590, charcoal #2C2A28. "
    "Matte gouache, flat shapes, no photorealism, no humans, no text, no letters, "
    "no logos, no watermarks, no Disney eyes."
)

SHOTS = [
    (
        "hero.png",
        "16:9 wide establishing painting of a flamingo agency flock roosting in a quiet olive grove at late afternoon. "
        "Five stylized flamingos with long S-necks: a tall director in matte pink at centre, a strategist with an olive sash, "
        "a tracker with a small sage monocle, an artist with ink-dipped wing tips, a host holding a tiny paper lantern. "
        "Cream sky, olive foliage, warm grey ground. Premium, still, cinematic. " + PALETTE,
    ),
    (
        "flo.png",
        "Character portrait, square, cream background. Flo, director flamingo: tall matte-pink bird, long S-neck, "
        "one gold-olive ring hovering near the beak, calm confident stance. Stamp illustration. " + PALETTE,
    ),
    (
        "bri.png",
        "Character portrait, square, cream background. Bri, strategist flamingo: dusty-rose body, olive sash, "
        "a single round sage bead like a rupee token. Stamp illustration. " + PALETTE,
    ),
    (
        "scout.png",
        "Character portrait, square, cream background. Scout, tracker flamingo: leaner grey-pink bird, "
        "small sage monocle over one eye, alert neck. Stamp illustration. " + PALETTE,
    ),
    (
        "inka.png",
        "Character portrait, square, cream background. Inka, artist flamingo: cream-pink body, wing tips dipped in charcoal ink, "
        "one olive drop of ink in the air. Stamp illustration. " + PALETTE,
    ),
    (
        "stella.png",
        "Character portrait, square, cream background. Stella, host flamingo: off-white and matte pink, "
        "tiny paper lantern hanging from the beak like a sign. Stamp illustration. " + PALETTE,
    ),
]


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    brief = g.text_client().models.generate_content(
        model=g.TEXT_MODEL,
        contents=(
            "You art-direct a flamingo flock for an Indian AI growth agency UI. "
            "Names: Flo director, Bri strategist, Scout tracker, Inka artist, Stella host. "
            "Return JSON with keys palette, world, birds (id, silhouette, prop). "
            "No people. Matte pinks, olive greens, off-whites, greys."
        ),
    )
    (OUT / "art-brief.json").write_text(
        json.dumps({"text": g.response_text(brief)}, indent=2),
        encoding="utf-8",
    )
    client = g.image_client()
    for name, prompt in SHOTS:
        print("==>", name, flush=True)
        resp = client.models.generate_content(
            model=g.IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            raise SystemExit(f"no image bytes for {name}: {g.response_text(resp)[:400]}")
        data, mime = blobs[0]
        dest = OUT / name
        dest.write_bytes(data)
        print("    wrote", dest, len(data), mime, flush=True)


if __name__ == "__main__":
    generate()

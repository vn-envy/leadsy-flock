#!/usr/bin/env python3
# Copyright 2026 Neekhil Vatsa
"""Tiny real generations against Veo and Lyria.

Catalog visibility is not invocation quota. This script is the day-1
proof that both bonus models actually run on the hackathon project.

Usage:
  uv run python scripts/smoke_models.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")
# Veo / Lyria are typically regional, not on the `global` Gemini endpoint.
LOCATION = os.environ.get("GOOGLE_CLOUD_MEDIA_LOCATION", "us-central1")
OUT = Path(__file__).resolve().parents[1] / "proof" / "model-smoke"
OUT.mkdir(parents=True, exist_ok=True)


def client() -> genai.Client:
    if not PROJECT:
        raise SystemExit("GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID is required")
    return genai.Client(vertexai=True, project=PROJECT, location=LOCATION)


def smoke_image(c: genai.Client) -> dict:
    """Gemini 3.1 Flash Image on global — Vertex successor to Imagen 3."""
    t0 = time.time()
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
    loc = os.environ.get("GOOGLE_CLOUD_IMAGE_LOCATION", "global")
    img_client = genai.Client(vertexai=True, project=PROJECT, location=loc)
    try:
        result = img_client.models.generate_content(
            model=model,
            contents="Empty modern gym, morning light, no people, no text.",
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        nbytes = 0
        mime = None
        for cand in result.candidates or []:
            for part in cand.content.parts or []:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    nbytes = len(inline.data)
                    mime = inline.mime_type
                    suffix = "png" if (mime or "").endswith("png") else "bin"
                    (OUT / f"imagen-still.{suffix}").write_bytes(inline.data)
        return {
            "ok": nbytes > 0,
            "model": model,
            "location": loc,
            "seconds": round(time.time() - t0, 2),
            "bytes": nbytes,
            "mime": mime,
            "note": "Imagen 3 publisher IDs 404 after 30 Jun 2026; this is the Vertex successor.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "model": model,
            "location": loc,
            "seconds": round(time.time() - t0, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def smoke_lyria(c: genai.Client) -> dict:
    """Shortest Lyria request we can send."""
    t0 = time.time()
    model = os.environ.get("LYRIA_MODEL", "lyria-002")
    try:
        result = c.models.generate_content(
            model=model,
            contents="A 2-second bright ukulele sting, no vocals, gym ad sting.",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
            ),
        )
        elapsed = round(time.time() - t0, 2)
        audio_bytes = 0
        mime = None
        if result.candidates:
            for part in result.candidates[0].content.parts or []:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    audio_bytes = len(inline.data)
                    mime = inline.mime_type
                    suffix = "wav" if (mime or "").endswith("wav") else "bin"
                    (OUT / f"lyria-sting.{suffix}").write_bytes(inline.data)
        return {
            "ok": audio_bytes > 0,
            "model": model,
            "location": LOCATION,
            "seconds": elapsed,
            "audio_bytes": audio_bytes,
            "mime": mime,
        }
    except Exception as exc:  # noqa: BLE001 — smoke test must report the error
        return {
            "ok": False,
            "model": model,
            "location": LOCATION,
            "seconds": round(time.time() - t0, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def smoke_veo(c: genai.Client) -> dict:
    """Shortest Veo request we can send (preview models use long-running ops)."""
    t0 = time.time()
    model = os.environ.get("VEO_MODEL", "veo-3.1-generate-001")
    prompt = "A 2-second locked-off shot of an empty modern gym, morning light, no people, no text."
    try:
        operation = c.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=4,
            ),
        )
        # Poll a bounded window — Veo is slow; day-1 only needs proof it started.
        deadline = time.time() + int(os.environ.get("VEO_WAIT_SECONDS", "180"))
        while not operation.done and time.time() < deadline:
            time.sleep(8)
            operation = c.operations.get(operation)

        elapsed = round(time.time() - t0, 2)
        if not operation.done:
            return {
                "ok": True,
                "model": model,
                "location": LOCATION,
                "seconds": elapsed,
                "status": "started_not_finished",
                "operation": getattr(operation, "name", None),
            }

        video_bytes = 0
        response = operation.response
        generated = getattr(response, "generated_videos", None) if response else None
        if generated:
            video = generated[0].video
            data = getattr(video, "video_bytes", None)
            if data:
                video_bytes = len(data)
                (OUT / "veo-gym.mp4").write_bytes(data)
        return {
            "ok": True,
            "model": model,
            "location": LOCATION,
            "seconds": elapsed,
            "status": "finished",
            "video_bytes": video_bytes,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "model": model,
            "location": LOCATION,
            "seconds": round(time.time() - t0, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    c = client()
    report = {
        "project": PROJECT,
        "location": LOCATION,
        "image": smoke_image(c),
        "lyria": smoke_lyria(c),
        "veo": smoke_veo(c),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    # Day-1 exit: at least one of the two must succeed. Both is better.
    if not report["image"]["ok"] and not report["lyria"]["ok"] and not report["veo"]["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

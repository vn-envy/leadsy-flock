# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Centre-crop masters into the 2026 paid-social ratios. Spec: design.md Asset kit."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app import media

# (slot, w, h) — used as aspect, not as exact output pixels.
IMAGE_SLOTS = (
    ("square", 1, 1, "still-square.png"),
    ("feed", 4, 5, "still-feed.png"),
    ("story", 9, 16, "still-story.png"),
    ("landscape", 191, 100, "still-landscape.png"),
)

VIDEO_SLOTS = (
    ("square", 1, 1, "clip-square.mp4"),
    ("feed", 4, 5, "clip-feed.mp4"),
    ("story", 9, 16, "clip-story.mp4"),
    ("landscape", 191, 100, "clip-landscape.mp4"),
)

_CROP_VF = (
    "crop="
    "'if(gte(iw/ih,{w}/{h}),ih*{w}/{h},iw)':"
    "'if(gte(iw/ih,{w}/{h}),ih,iw*{h}/{w})'"
)


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def crop_filter(rw: int, rh: int) -> str:
    return _CROP_VF.format(w=rw, h=rh)


def derive_images(campaign_id: str, source_stem: str, *, prefer: set[str] | None = None) -> dict[str, Any]:
    found = None
    for name in (f"{source_stem}.png", f"{source_stem}.jpg", source_stem):
        found = media.get_bytes(media.campaign_path(campaign_id, name))
        if found:
            break
    if not found:
        return {"ok": False, "error": "no_source"}
    data, _mime = found
    return _derive_bytes(campaign_id, data, IMAGE_SLOTS, video=False, prefer=prefer)


def derive_videos(campaign_id: str, source_name: str = "clip.mp4") -> dict[str, Any]:
    found = media.get_bytes(media.campaign_path(campaign_id, source_name))
    if not found:
        return {"ok": False, "error": "no_source"}
    data, _mime = found
    return _derive_bytes(campaign_id, data, VIDEO_SLOTS, video=True, prefer=None)


def _derive_bytes(
    campaign_id: str,
    data: bytes,
    slots: tuple,
    *,
    video: bool,
    prefer: set[str] | None,
) -> dict[str, Any]:
    bin_path = ffmpeg_bin()
    if not bin_path:
        return {"ok": False, "error": "ffmpeg_missing"}
    out: dict[str, Any] = {"ok": True, "slots": {}}
    suffix = ".mp4" if video else ".png"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"src{suffix}"
        src.write_bytes(data)
        for slot, rw, rh, filename in slots:
            if prefer is not None and slot not in prefer:
                continue
            dest = Path(tmp) / filename
            cmd = [
                bin_path,
                "-y",
                "-i",
                str(src),
                "-vf",
                crop_filter(rw, rh),
            ]
            if video:
                cmd += ["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
            else:
                cmd += ["-frames:v", "1"]
            cmd.append(str(dest))
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                out["slots"][slot] = {"ok": False, "error": str(exc)[:200]}
                continue
            if not dest.exists() or dest.stat().st_size < 32:
                out["slots"][slot] = {"ok": False, "error": "empty"}
                continue
            mime = "video/mp4" if video else "image/png"
            uri = media.put_bytes(media.campaign_path(campaign_id, filename), dest.read_bytes(), mime)
            public = f"/media/{campaign_id}/{filename.rsplit('.', 1)[0]}"
            out["slots"][slot] = {
                "ok": True,
                "gcs": uri,
                "bytes": dest.stat().st_size,
                "publicPath": public,
                "aspect": f"{rw}:{rh}" if (rw, rh) != (191, 100) else "1.91:1",
            }
    return out

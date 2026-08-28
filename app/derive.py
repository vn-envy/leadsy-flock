# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Centre-crop masters into declared channel pixels. Spec: design.md Asset kit."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app import media

# slot, aspect w, aspect h, output width, output height, suffix
IMAGE_SLOTS = (
    ("square", 1, 1, 1080, 1080, "still-square.png"),
    ("feed", 4, 5, 1080, 1350, "still-feed.png"),
    ("story", 9, 16, 1080, 1920, "still-story.png"),
    ("landscape", 191, 100, 1200, 628, "still-landscape.png"),
)

VIDEO_SLOT_BOXES = (
    ("square", 1, 1, 1080, 1080),
    ("feed", 4, 5, 1080, 1350),
    ("story", 9, 16, 1080, 1920),
    ("landscape", 191, 100, 1200, 628),
)

PIXEL_BOXES: dict[str, tuple[int, int, str]] = {
    "square": (1080, 1080, "1:1"),
    "feed": (1080, 1350, "4:5"),
    "story": (1080, 1920, "9:16"),
    "landscape": (1200, 628, "1.91:1"),
}

_CROP_VF = (
    "crop="
    "'if(gte(iw/ih,{w}/{h}),ih*{w}/{h},iw)':"
    "'if(gte(iw/ih,{w}/{h}),ih,iw*{h}/{w})',"
    "scale={pw}:{ph}:flags=lanczos,setsar=1"
)


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def crop_filter(rw: int, rh: int, pw: int | None = None, ph: int | None = None) -> str:
    if pw is None or ph is None:
        box = next((b for b in VIDEO_SLOT_BOXES if b[1] == rw and b[2] == rh), None)
        pw = box[3] if box else rw
        ph = box[4] if box else rh
    return _CROP_VF.format(w=rw, h=rh, pw=pw, ph=ph)


def video_encode_args(*, audio: bool = True) -> list[str]:
    args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio:
        args += ["-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-an"]
    return args


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


def derive_videos(
    campaign_id: str,
    source_name: str = "clip.mp4",
    *,
    prefix: str = "clip",
) -> dict[str, Any]:
    found = media.get_bytes(media.campaign_path(campaign_id, source_name))
    if not found:
        return {"ok": False, "error": "no_source"}
    data, _mime = found
    slots = tuple(
        (slot, rw, rh, pw, ph, f"{prefix}-{slot}.mp4")
        for slot, rw, rh, pw, ph in VIDEO_SLOT_BOXES
    )
    return _derive_bytes(campaign_id, data, slots, video=True, prefer=None)


def download_name(campaign_id: str, slot: str) -> str:
    key = slot.replace("clip-proof-", "").replace("clip-", "").replace("still-", "")
    if key in ("en", "indic", "captioned", "captioned-en"):
        key = "story"
    box = PIXEL_BOXES.get(key)
    ext = "mp4" if slot.startswith("clip") else "png"
    if not box:
        return f"{campaign_id}-{slot}.{ext}"
    pw, ph, _aspect = box
    return f"{campaign_id}-{slot}-{pw}x{ph}.{ext}"


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
        for slot, rw, rh, *rest in slots:
            if prefer is not None and slot not in prefer:
                continue
            if video:
                pw, ph, filename = rest
            else:
                pw, ph, filename = rest
            dest = Path(tmp) / filename
            vf = crop_filter(rw, rh, pw, ph)
            cmd = [
                bin_path,
                "-y",
                "-i",
                str(src),
                "-vf",
                vf,
            ]
            if video:
                cmd += video_encode_args()
            else:
                cmd += ["-frames:v", "1"]
            cmd.append(str(dest))
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=90)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                if video:
                    silent = [
                        bin_path,
                        "-y",
                        "-i",
                        str(src),
                        "-vf",
                        vf,
                        *video_encode_args(audio=False),
                        str(dest),
                    ]
                    try:
                        subprocess.run(silent, check=True, capture_output=True, timeout=90)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                        out["slots"][slot] = {"ok": False, "error": str(exc)[:200]}
                        continue
                else:
                    out["slots"][slot] = {"ok": False, "error": str(exc)[:200]}
                    continue
            if not dest.exists() or dest.stat().st_size < 32:
                out["slots"][slot] = {"ok": False, "error": "empty"}
                continue
            mime = "video/mp4" if video else "image/png"
            uri = media.put_bytes(media.campaign_path(campaign_id, filename), dest.read_bytes(), mime)
            public = f"/media/{campaign_id}/{filename.rsplit('.', 1)[0]}"
            aspect = PIXEL_BOXES[slot][2]
            out["slots"][slot] = {
                "ok": True,
                "gcs": uri,
                "bytes": dest.stat().st_size,
                "publicPath": public,
                "aspect": aspect,
                "width": pw,
                "height": ph,
            }
    return out

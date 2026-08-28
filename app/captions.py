# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Safe-zone captions for 9:16 only. Veo never burns type — ffmpeg may."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app import media
from app.derive import ffmpeg_bin

_FONT_HINTS = {
    "hi": ("Devanagari", "Deva"),
    "mr": ("Devanagari", "Deva"),
    "gu": ("Gujarati", "Gujr"),
    "kn": ("Kannada", "Knda"),
    "ta": ("Tamil", "Taml"),
    "te": ("Telugu", "Telu"),
    "ml": ("Malayalam", "Mlym"),
    "bn": ("Bengali", "Beng"),
    "pa": ("Gurmukhi", "Guru"),
}


def indic_font(code: str) -> str | None:
    hints = _FONT_HINTS.get(code or "hi", ("Devanagari", "Deva"))
    roots = (
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/lohit-devanagari"),
        Path("/usr/share/fonts/truetype"),
        Path("/usr/share/fonts"),
    )
    names = [
        f"NotoSans{hints[0]}-Regular.ttf",
        f"NotoSans{hints[0]}-Regular.otf",
        f"Lohit-{hints[0]}.ttf",
        "NotoSans-Regular.ttf",
    ]
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            hit = root / name
            if hit.is_file():
                return str(hit)
        for hit in root.rglob("*.ttf"):
            stem = hit.stem.lower()
            if hints[0].lower() in stem or hints[1].lower() in stem:
                return str(hit)
    return shutil.which("fc-list") and None


def ass_document(text: str, *, font: str = "Noto Sans") -> str:
    line = _ass_escape(_wrap(text, 28))
    font_name = Path(font).stem.replace("-Regular", "").replace("NotoSans", "Noto Sans ")
    if font_name.startswith("Noto Sans"):
        style_font = font_name.replace("Noto Sans", "Noto Sans ").replace("  ", " ").strip()
        if style_font == "Noto Sans":
            style_font = "Noto Sans"
    else:
        style_font = "Noto Sans"
    # Use the file's family-ish name; ffmpeg subtitles filter loads fontsdir.
    family = _family_from_path(font) or "Noto Sans"
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 1\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{family},46,&H00FFFFFF,&H000000FF,&H64000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,3,0,2,90,90,320,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.50,0:00:07.60,Default,,0,0,0,,{line}\n"
    )


def burn_story_captions(
    campaign_id: str,
    text: str,
    locale: dict[str, str] | None,
    *,
    dest_name: str = "clip-captioned.mp4",
) -> dict[str, Any]:
    """Overlay captions on clip-story.mp4. No-op if text or ffmpeg missing."""
    text = " ".join((text or "").split())
    if not text or not campaign_id:
        return {"ok": False, "skipped": True, "reason": "no_text"}
    found = media.get_bytes(media.campaign_path(campaign_id, "clip-story.mp4"))
    if not found:
        found = media.get_bytes(media.campaign_path(campaign_id, "clip.mp4"))
    if not found:
        return {"ok": False, "error": "no_source"}
    data, _mime = found
    bin_path = ffmpeg_bin()
    if not bin_path:
        return {"ok": False, "error": "ffmpeg_missing"}
    code = (locale or {}).get("code") or "hi"
    font = indic_font(code)
    ass = ass_document(text, font=font or "Noto Sans")
    media.put_bytes(media.campaign_path(campaign_id, "captions.ass"), ass.encode("utf-8"), "text/plain")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src.mp4"
        sub = Path(tmp) / "captions.ass"
        dest = Path(tmp) / "out.mp4"
        src.write_bytes(data)
        sub.write_text(ass, encoding="utf-8")
        fontsdir = str(Path(font).parent) if font else "/usr/share/fonts"
        vf = f"subtitles={sub.as_posix()}:fontsdir={fontsdir}"
        cmd = [
            bin_path,
            "-y",
            "-i",
            str(src),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(dest),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=90)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            return {"ok": False, "error": str(exc)[:220], "ass": True}
        if not dest.exists() or dest.stat().st_size < 32:
            return {"ok": False, "error": "empty"}
        uri = media.put_bytes(
            media.campaign_path(campaign_id, dest_name),
            dest.read_bytes(),
            "video/mp4",
        )
        stem = dest_name.rsplit(".", 1)[0]
        return {
            "ok": True,
            "gcs": uri,
            "bytes": dest.stat().st_size,
            "publicPath": f"/media/{campaign_id}/{stem}",
            "font": font,
        }


def _family_from_path(font: str) -> str:
    stem = Path(font).stem.replace("-Regular", "").replace("-Bold", "")
    if stem.startswith("NotoSans"):
        rest = stem[len("NotoSans") :]
        return f"Noto Sans {rest}".strip() if rest else "Noto Sans"
    if stem.startswith("Lohit-"):
        return stem.replace("-", " ")
    return "Noto Sans"


def _wrap(text: str, width: int) -> str:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if len(trial) > width and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return "\\N".join(lines[:3])


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")

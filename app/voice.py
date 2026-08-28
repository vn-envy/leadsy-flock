# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""English + one Indic spoken line, muxed onto the harvested Veo picture."""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from google.genai import types

from app import media
from app.derive import ffmpeg_bin, video_encode_args
from app.engines import gemini_util as g

TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
_VOICE_EN = os.environ.get("GEMINI_TTS_VOICE_EN", "Kore")
_VOICE_INDIC = os.environ.get("GEMINI_TTS_VOICE_INDIC", "Puck")


def speak(text: str, *, language: str, voice: str | None = None) -> dict[str, Any]:
    """Gemini TTS. Returns audio bytes or a skipped/error record — never raises."""
    line = " ".join((text or "").split())
    if not line:
        return {"ok": False, "skipped": True, "reason": "no_text"}
    voice = voice or (_VOICE_EN if language.startswith("en") else _VOICE_INDIC)
    prompt = (
        f"Speak this line clearly in {language}, natural, unhurried, no extra words:\n{line}"
    )
    try:
        client = g.media_client()
        resp = client.models.generate_content(
            model=TTS_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            return {"ok": False, "error": "no_audio", "model": TTS_MODEL}
        data, mime = blobs[0]
        mime = mime or "audio/wav"
        if "l16" in mime.lower() or "pcm" in mime.lower():
            rate = 24000
            if "rate=" in mime.lower():
                try:
                    rate = int(mime.lower().split("rate=", 1)[-1].split(";")[0])
                except ValueError:
                    rate = 24000
            data = _pcm_to_wav(data, rate=rate)
            mime = "audio/wav"
        return {
            "ok": True,
            "model": TTS_MODEL,
            "bytes": len(data),
            "mime": mime,
            "_bytes": data,
            "voice": voice,
            "language": language,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "model": TTS_MODEL,
            "error": f"{type(exc).__name__}:{exc}"[:300],
            "quotaLikely": "429" in str(exc),
        }


def mux_over_video(
    campaign_id: str,
    audio: bytes,
    *,
    dest_name: str,
    source_name: str = "clip-story.mp4",
) -> dict[str, Any]:
    """Replace (or mix under) Veo room-tone with a spoken line. Picture stays the shop film."""
    found = media.get_bytes(media.campaign_path(campaign_id, source_name))
    if not found:
        found = media.get_bytes(media.campaign_path(campaign_id, "clip.mp4"))
    if not found:
        return {"ok": False, "error": "no_source"}
    video, _vmime = found
    bin_path = ffmpeg_bin()
    if not bin_path:
        return {"ok": False, "error": "ffmpeg_missing"}
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src.mp4"
        vo = Path(tmp) / "vo.bin"
        dest = Path(tmp) / "out.mp4"
        src.write_bytes(video)
        vo.write_bytes(audio)
        cmd = [
            bin_path,
            "-y",
            "-i",
            str(src),
            "-i",
            str(vo),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            *video_encode_args(audio=True),
            str(dest),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=90)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            return {"ok": False, "error": str(exc)[:220]}
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
        }


def dual_tracks(
    campaign_id: str,
    copy: dict[str, Any],
    locale: dict[str, Any] | None,
) -> dict[str, Any]:
    """Always English. Indic when the geo is not English-only."""
    locale = locale or {}
    out: dict[str, Any] = {}
    vo_en = str(copy.get("voEn") or "")
    vo_loc = str(copy.get("voIndic") or "")
    en = speak(vo_en, language="English", voice=_VOICE_EN)
    if en.get("_bytes"):
        raw = en.pop("_bytes")
        media.put_bytes(media.campaign_path(campaign_id, "vo-en.bin"), raw, en.get("mime") or "audio/wav")
        muxed = mux_over_video(campaign_id, raw, dest_name="clip-en.mp4")
        out["en"] = {**en, **muxed}
    else:
        out["en"] = en
    if vo_loc and (locale.get("code") or "hi") != "en":
        lang = str(locale.get("language") or "Hindi")
        loc = speak(vo_loc, language=lang, voice=_VOICE_INDIC)
        if loc.get("_bytes"):
            raw = loc.pop("_bytes")
            media.put_bytes(media.campaign_path(campaign_id, "vo-indic.bin"), raw, loc.get("mime") or "audio/wav")
            muxed = mux_over_video(campaign_id, raw, dest_name="clip-indic.mp4")
            out["indic"] = {**loc, **muxed}
        else:
            out["indic"] = loc
    return out


def _pcm_to_wav(pcm: bytes, *, rate: int = 24000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as fh:
        fh.setnchannels(channels)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(pcm)
    return buf.getvalue()

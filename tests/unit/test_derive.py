# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

import shutil
import subprocess
from pathlib import Path

import pytest

from app.derive import crop_filter, derive_images, derive_videos, ffmpeg_bin


def test_crop_filter_keeps_subject_in_frame() -> None:
    vf = crop_filter(9, 16)
    assert "9/16" in vf
    assert "iw/ih" in vf
    assert crop_filter(191, 100).count("191/100") >= 1


@pytest.mark.skipif(not ffmpeg_bin(), reason="ffmpeg not installed")
def test_derive_images_centre_crops_square(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "still.png"
    subprocess.run(
        [
            ffmpeg_bin(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x180:d=1",
            "-frames:v",
            "1",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    stored: dict[str, tuple[bytes, str]] = {}

    def get_bytes(path: str):
        if path.endswith("still.png"):
            return src.read_bytes(), "image/png"
        return stored.get(path)

    def put_bytes(path: str, data: bytes, mime: str) -> str:
        stored[path] = (data, mime)
        return f"gs://t/{path}"

    monkeypatch.setattr("app.derive.media.get_bytes", get_bytes)
    monkeypatch.setattr("app.derive.media.put_bytes", put_bytes)
    monkeypatch.setattr("app.derive.media.campaign_path", lambda cid, name: f"{cid}/{name}")

    out = derive_images("c1", "still", prefer={"square"})
    assert out["ok"] is True
    assert out["slots"]["square"]["ok"] is True
    assert "feed" not in out["slots"]
    png = stored["c1/still-square.png"][0]
    dest = tmp_path / "square.png"
    dest.write_bytes(png)
    w, h = _probe_wh(dest)
    assert w == h


@pytest.mark.skipif(not ffmpeg_bin(), reason="ffmpeg not installed")
def test_derive_videos_writes_story_slot(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "clip.mp4"
    subprocess.run(
        [
            ffmpeg_bin(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x180:d=1",
            "-pix_fmt",
            "yuv420p",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    stored: dict[str, tuple[bytes, str]] = {}

    def get_bytes(path: str):
        if path.endswith("clip.mp4"):
            return src.read_bytes(), "video/mp4"
        return stored.get(path)

    def put_bytes(path: str, data: bytes, mime: str) -> str:
        stored[path] = (data, mime)
        return f"gs://t/{path}"

    monkeypatch.setattr("app.derive.media.get_bytes", get_bytes)
    monkeypatch.setattr("app.derive.media.put_bytes", put_bytes)
    monkeypatch.setattr("app.derive.media.campaign_path", lambda cid, name: f"{cid}/{name}")

    out = derive_videos("c1", "clip.mp4")
    assert out["ok"] is True
    assert out["slots"]["story"]["ok"] is True
    assert stored["c1/clip-story.mp4"][1] == "video/mp4"
    dest = tmp_path / "story.mp4"
    dest.write_bytes(stored["c1/clip-story.mp4"][0])
    w, h = _probe_wh(dest)
    assert abs((w / h) - (9 / 16)) < 0.08


def _probe_wh(path: Path) -> tuple[int, int]:
    probe = shutil.which("ffprobe") or ffmpeg_bin()
    cmd = [
        probe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0",
        str(path),
    ]
    if Path(probe).name == "ffmpeg":
        cmd = [probe, "-i", str(path)]
        raw = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # ffmpeg -i prints stream info on stderr
        for token in (raw.stderr or "").replace(",", " ").split():
            if "x" in token and token[0].isdigit():
                w, _, h = token.partition("x")
                if w.isdigit() and h.isdigit():
                    return int(w), int(h)
        raise AssertionError(raw.stderr)
    raw = subprocess.run(cmd, capture_output=True, text=True, check=True)
    w, h = raw.stdout.strip().split(",")
    return int(w), int(h)

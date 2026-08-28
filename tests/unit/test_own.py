# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.own import collect_uris, extract_html_images, is_image, sanitize_own_uris
from app.voice import _pcm_to_wav


def test_pcm_wraps_as_wav() -> None:
    wav = _pcm_to_wav(b"\x00\x00" * 24, rate=24000)
    assert wav[:4] == b"RIFF"
    assert b"WAVE" in wav[:16]


def test_collect_uris_from_brief_and_scout() -> None:
    rows = collect_uris(
        {
            "website": "https://noya.example/salon",
            "assetUris": [
                "https://cdn.example/shop.jpg",
                "not-a-url",
                "https://www.facebook.com/people/Jane/1",
            ],
            "menuUrl": "https://noya.example/menu.pdf",
        },
        {
            "ownUris": [{"uri": "https://maps.google.com/?cid=1", "kind": "maps"}],
            "evidence": [{"uri": "https://noya.example/chair.png", "source": "url"}],
        },
    )
    uris = [r["uri"] for r in rows]
    assert "https://noya.example/salon" in uris
    assert "https://cdn.example/shop.jpg" in uris
    assert "https://noya.example/menu.pdf" in uris
    assert "https://maps.google.com/?cid=1" in uris
    assert "https://noya.example/chair.png" in uris
    assert all("facebook.com/people" not in u for u in uris)


def test_extract_html_images_uses_og_and_skips_icons() -> None:
    html = """
    <html><head>
      <meta property="og:image" content="/photos/interior.jpg"/>
    </head><body>
      <img src="https://cdn.example/logo.png"/>
      <img src="/photos/bowl.webp"/>
      <img src="data:image/gif;base64,xx"/>
    </body></html>
    """
    urls = extract_html_images(html, "https://noya.example/")
    assert "https://noya.example/photos/interior.jpg" in urls
    assert "https://noya.example/photos/bowl.webp" in urls
    assert all("logo" not in u for u in urls)
    assert all(not u.startswith("data:") for u in urls)


def test_is_image_magic() -> None:
    assert is_image(b"\xff\xd8\xff\xe0rest", "application/octet-stream")
    assert is_image(b"hello", "image/jpeg")
    assert not is_image(b"<html>", "text/html")


def test_sanitize_own_uris_keeps_brief_website() -> None:
    rows = sanitize_own_uris(
        [{"uri": "https://noya.example/a.jpg", "kind": "photo"}],
        website="https://noya.example/",
    )
    assert rows[0]["uri"] == "https://noya.example/"
    assert rows[0]["kind"] == "website"
    assert rows[1]["kind"] == "photo"

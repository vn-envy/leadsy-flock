# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Pull the shop's own photos / pages / menus, then optionally clean them.

Gemini generates a still from scratch only when nothing usable arrives.
Otherwise it is a refine/filler layer on real presence.
"""

from __future__ import annotations

import html as html_lib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from google.genai import types

from app import media
from app.engines import gemini_util as g
from app.vertical import infer_role

MAX_URIS = 8
MAX_BYTES = 6 * 1024 * 1024
FETCH_TIMEOUT = 8
_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"RIFF", b"GIF8")
_SKIP_HOST_BITS = ("facebook.com/people", "instagram.com/p/", "tiktok.com/@")


def sanitize_own_uris(
    raw: Any,
    *,
    extra_uris: list[str] | None = None,
    website: str = "",
) -> list[dict[str, str]]:
    allowed = {"website", "maps", "listing", "menu", "pdf", "photo"}
    rows = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(uri: str, kind: str, title: str = "") -> None:
        u = (uri or "").strip()
        if not u.startswith("http") or u in seen:
            return
        seen.add(u)
        k = kind if kind in allowed else "photo"
        out.append(
            {
                "uri": u[:500],
                "kind": k,
                "title": (title or k)[:160],
                "role": infer_role(u, k, title),
            }
        )

    _add(website, "website", "brief website")
    for item in rows:
        if isinstance(item, str):
            _add(item, "photo")
        elif isinstance(item, dict):
            _add(str(item.get("uri") or ""), str(item.get("kind") or "photo"), str(item.get("title") or ""))
    for u in extra_uris or []:
        _add(str(u), "listing" if "maps" in str(u) else "photo")
        if len(out) >= 8:
            break
    return out[:8]


def collect_uris(brief: dict[str, Any] | None, scout: dict[str, Any] | None) -> list[dict[str, str]]:
    brief = brief or {}
    scout = scout or {}
    rows: list[dict[str, str]] = []

    def _add(uri: Any, kind: str, role: str = "") -> None:
        u = str(uri or "").strip()
        if not u.startswith("http"):
            return
        low = u.lower()
        if any(b in low for b in _SKIP_HOST_BITS):
            return
        if any(r["uri"] == u for r in rows):
            return
        rows.append({"uri": u, "kind": kind, "role": role or infer_role(u, kind)})

    for key, kind in (
        ("website", "website"),
        ("site", "website"),
        ("googleListing", "listing"),
        ("mapsUrl", "maps"),
        ("menuUrl", "menu"),
    ):
        _add(brief.get(key), kind)
    extra = brief.get("assetUris") or brief.get("photos") or []
    if isinstance(extra, str):
        extra = [extra]
    for u in extra:
        kind = "pdf" if str(u).lower().endswith(".pdf") else "photo"
        _add(u, kind)
    for item in scout.get("ownUris") or []:
        if isinstance(item, str):
            _add(item, "photo")
        elif isinstance(item, dict):
            _add(item.get("uri"), str(item.get("kind") or "photo"), str(item.get("role") or ""))
    for ev in scout.get("evidence") or []:
        uri = str((ev or {}).get("uri") or "")
        src = str((ev or {}).get("source") or "")
        if uri.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf")):
            _add(uri, "pdf" if uri.lower().endswith(".pdf") else "photo")
        elif src in ("maps", "url") and (
            "google.com/maps" in uri or "maps.google.com" in uri or "share.google/" in uri
        ):
            _add(uri, "maps")
    # A menu PDF on the shop's own host is also a homepage we can pull og:images from.
    for row in list(rows):
        if row["kind"] in ("menu", "pdf"):
            parsed = urlparse(row["uri"])
            if parsed.scheme in ("http", "https") and parsed.netloc:
                _add(f"{parsed.scheme}://{parsed.netloc}/", "website")
    return rows[:MAX_URIS]


class _ImgParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: v or "" for k, v in attrs}
        if tag == "meta" and ad.get("property") in ("og:image", "og:image:url", "twitter:image"):
            if ad.get("content"):
                self.urls.append(ad["content"])
        if tag == "img":
            src = ad.get("src") or ad.get("data-src") or ""
            if src:
                self.urls.append(src)
        style = ad.get("style") or ""
        if "url(" in style.lower():
            self.urls.extend(_css_urls(style))


_CSS_URL = re.compile(
    r"url\(\s*['\"]?([^)'\"]+\.(?:jpg|jpeg|png|webp|gif))['\"]?\s*\)",
    re.IGNORECASE,
)


def _css_urls(raw: str) -> list[str]:
    return [m.group(1).strip() for m in _CSS_URL.finditer(raw or "")]


def extract_html_images(raw: str, base: str, *, limit: int = 6) -> list[str]:
    parser = _ImgParser()
    try:
        parser.feed(raw)
    except Exception:  # noqa: BLE001
        return []
    candidates = list(parser.urls)
    candidates.extend(_css_urls(raw))
    out: list[str] = []
    for u in candidates:
        abs_u = urljoin(base, html_lib.unescape(u).strip())
        if not abs_u.startswith("http"):
            continue
        path = urlparse(abs_u).path.lower()
        if any(tok in path for tok in ("logo", "icon", "sprite", "pixel", "1x1", "favicon", "background-1", "bg2")):
            continue
        if abs_u not in out:
            out.append(abs_u)
        if len(out) >= limit:
            break
    return out


def fetch_bytes(uri: str) -> tuple[bytes, str] | None:
    req = Request(uri, headers={"User-Agent": "LeadsyFlock/1.0 (owner-asset fetch)"})
    try:
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310 — http(s) only, checked by caller
            ctype = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            data = resp.read(MAX_BYTES + 1)
    except Exception:  # noqa: BLE001
        return None
    if not data or len(data) > MAX_BYTES:
        return None
    return data, ctype or "application/octet-stream"


def is_image(data: bytes, ctype: str) -> bool:
    if ctype.startswith("image/"):
        return True
    return any(data.startswith(m) for m in _IMAGE_MAGIC)


def gather(
    campaign_id: str,
    brief: dict[str, Any],
    scout: dict[str, Any],
    *,
    fetch=fetch_bytes,
    refine=True,
) -> dict[str, Any]:
    """Download owner/listing assets. Never invent a shop that has no photos."""
    errors: list[str] = []
    frames: list[dict[str, Any]] = []
    tried = collect_uris(brief, scout)
    expanded: list[dict[str, str]] = list(tried)
    for row in list(tried):
        if row["kind"] in ("website", "listing", "maps", "menu") and not row["uri"].lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".pdf")
        ):
            got = fetch(row["uri"])
            if not got:
                errors.append(f"fetch:{row['uri'][:80]}")
                continue
            data, ctype = got
            if "html" in ctype or data.lstrip()[:15].lower().startswith(b"<!doctype") or data.lstrip()[:6].lower().startswith(b"<html"):
                for img in extract_html_images(data.decode("utf-8", "ignore"), row["uri"]):
                    expanded.append({"uri": img, "kind": "photo", "from": row["uri"]})
            elif is_image(data, ctype) or "pdf" in ctype:
                rec = _store_raw(campaign_id, data, ctype, row, len(frames), errors)
                if rec:
                    frames.append(rec)
    photo_rows = [r for r in expanded if r.get("kind") in ("photo", "pdf") or r["uri"].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf"))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fetch, r["uri"]): r for r in photo_rows[:MAX_URIS]}
        for fut in as_completed(futs):
            row = futs[fut]
            try:
                got = fut.result()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"fetch:{type(exc).__name__}")
                continue
            if not got:
                continue
            data, ctype = got
            rec = _store_raw(campaign_id, data, ctype, row, len(frames), errors)
            if rec:
                frames.append(rec)
            if len(frames) >= 6:
                break

    usable = [f for f in frames if f.get("ok")]
    if refine and usable:
        for rec in usable[:3]:
            cleaned = _refine(rec, brief, errors)
            if cleaned:
                rec.update(cleaned)
                rec["refined"] = True

    origin = "own" if usable else "none"
    return {
        "origin": origin,
        "tried": tried,
        "frames": usable,
        "errors": errors,
        "count": len(usable),
    }


def apply_to_stills(
    campaign_id: str,
    pack: dict[str, Any],
) -> dict[str, Any]:
    """Map owner frames onto still / still-story / still-detail (proof → detail)."""
    frames = list(pack.get("frames") or [])
    slots = ("still", "still-story", "still-detail")
    kinds = {"interior": "still", "listing": "still", "product": "still-detail", "menu": "still-detail", "photo": "still-story"}
    assigned: dict[str, dict[str, Any]] = {}
    leftover = []
    for rec in frames:
        role = str(rec.get("role") or infer_role(str(rec.get("uri") or ""), str(rec.get("kind") or "")))
        rec["role"] = role
        if role == "proof":
            want = "still-detail"
        else:
            want = kinds.get(str(rec.get("kind") or "photo"), "still")
        if want not in assigned:
            assigned[want] = rec
        else:
            leftover.append(rec)
    for slot in slots:
        if slot in assigned:
            continue
        if leftover:
            assigned[slot] = leftover.pop(0)
    written: dict[str, Any] = {}
    for slot, rec in assigned.items():
        data = rec.get("_bytes")
        mime = rec.get("mime") or "image/jpeg"
        if not data:
            continue
        ext = "png" if "png" in mime else "jpg"
        name = f"{slot}.{ext}" if slot == "still" else f"{slot}.png"
        if slot != "still" and "jpeg" in mime:
            name = f"{slot}.jpg"
        uri = media.put_bytes(media.campaign_path(campaign_id, name), data, mime)
        rec = dict(rec)
        rec.pop("_bytes", None)
        rec.update(
            {
                "ok": True,
                "gcs": uri,
                "publicPath": f"/media/{campaign_id}/{slot}",
                "origin": "own",
                "bytes": len(data) if isinstance(data, (bytes, bytearray)) else rec.get("bytes"),
                "_bytes": data,
            }
        )
        written[slot] = rec
    return written


def _store_raw(
    campaign_id: str,
    data: bytes,
    ctype: str,
    row: dict[str, str],
    idx: int,
    errors: list[str],
) -> dict[str, Any] | None:
    if "pdf" in ctype or row["uri"].lower().endswith(".pdf"):
        still = _still_from_pdf(campaign_id, data, row, errors)
        return still
    if not is_image(data, ctype):
        return None
    if len(data) < 4000:
        return None
    mime = ctype if ctype.startswith("image/") else "image/jpeg"
    stem = f"own-{idx}"
    ext = "png" if "png" in mime else "jpg"
    uri = media.put_bytes(media.campaign_path(campaign_id, f"{stem}.{ext}"), data, mime)
    return {
        "ok": True,
        "uri": row["uri"],
        "kind": row.get("kind") or "photo",
        "role": infer_role(row.get("uri") or "", row.get("kind") or "", row.get("title") or ""),
        "gcs": uri,
        "mime": mime,
        "bytes": len(data),
        "publicPath": f"/media/{campaign_id}/{stem}",
        "origin": "own",
        "_bytes": data,
    }


def _still_from_pdf(
    campaign_id: str, data: bytes, row: dict[str, str], errors: list[str]
) -> dict[str, Any] | None:
    """Read a real menu/PDF, emit one cleaned still of what is actually on the page."""
    try:
        client = g.image_client()
        resp = client.models.generate_content(
            model=g.IMAGE_MODEL,
            contents=[
                types.Part.from_bytes(data=data, mime_type="application/pdf"),
                "Photograph the real product or interior shown in this document. "
                "Keep the same items. No people, no invented shop, no extra text.",
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            errors.append("pdf:no_image")
            return None
        img, mime = blobs[0]
        uri = media.put_bytes(media.campaign_path(campaign_id, "own-menu.png"), img, mime or "image/png")
        return {
            "ok": True,
            "uri": row["uri"],
            "kind": "menu",
            "role": "proof",
            "gcs": uri,
            "mime": mime or "image/png",
            "bytes": len(img),
            "origin": "own-pdf",
            "_bytes": img,
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pdf:{type(exc).__name__}:{exc}")
        return None


def _refine(rec: dict[str, Any], brief: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    data = rec.get("_bytes")
    mime = rec.get("mime") or "image/jpeg"
    if not data:
        return None
    name = str(brief.get("businessName") or "this shop")
    prompt = (
        f"Clean this real photograph of {name}. Same room and products. "
        "Even the lighting, lift shadows, remove clutter, people, and watermarks. "
        "Do not invent a different interior or brand. No on-image text, no faces, no hands."
    )
    try:
        client = g.image_client()
        resp = client.models.generate_content(
            model=g.IMAGE_MODEL,
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                prompt,
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            return None
        img, out_mime = blobs[0]
        if len(img) < 4000:
            return None
        return {"_bytes": img, "mime": out_mime or "image/png", "bytes": len(img)}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"refine:{type(exc).__name__}:{exc}")
        return None

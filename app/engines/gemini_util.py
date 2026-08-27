# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Vertex Gemini clients: global for text+grounding, us-central1 for media."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.settings import load_settings

TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.5-flash")
# Imagen 3 (`imagen-3.0-generate-002`) was discontinued 30 Jun 2026 on Vertex.
# Official successor: Gemini image models. 3.1 Flash Image lives on `global`.
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
IMAGE_FALLBACK_MODEL = os.environ.get("GEMINI_IMAGE_FALLBACK_MODEL", "gemini-2.5-flash-image")
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-generate-001")
LYRIA_MODEL = os.environ.get("LYRIA_MODEL", "lyria-002")
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma-3-12b-it")


@lru_cache(maxsize=2)
def text_client() -> genai.Client:
    """Keep one Vertex client alive. google-genai 2.x closes ephemeral clients."""
    s = load_settings()
    return genai.Client(
        vertexai=True,
        project=s.project_id,
        location=s.location_global or "global",
    )


@lru_cache(maxsize=2)
def media_client() -> genai.Client:
    s = load_settings()
    loc = os.environ.get("GOOGLE_CLOUD_MEDIA_LOCATION") or "us-central1"
    return genai.Client(vertexai=True, project=s.project_id, location=loc)


@lru_cache(maxsize=2)
def image_client() -> genai.Client:
    """Gemini 3.1 Flash Image is on the global endpoint, not us-central1."""
    s = load_settings()
    loc = os.environ.get("GOOGLE_CLOUD_IMAGE_LOCATION") or "global"
    return genai.Client(vertexai=True, project=s.project_id, location=loc)


def extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).removesuffix("```").strip()
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else {"value": out}
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            out = json.loads(raw[start : end + 1])
            return out if isinstance(out, dict) else {"value": out}
        raise


def grounding_uris(response: Any) -> list[str]:
    uris: list[str] = []
    meta = getattr(response, "candidates", [None])[0]
    if not meta:
        return uris
    gm = getattr(meta, "grounding_metadata", None)
    chunks = getattr(gm, "grounding_chunks", None) or []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) if web else None
        maps = getattr(chunk, "maps", None)
        maps_uri = getattr(maps, "uri", None) if maps else None
        place = getattr(maps, "place_id", None) if maps else None
        if uri:
            uris.append(uri)
        if maps_uri:
            uris.append(maps_uri)
        elif place:
            uris.append(f"https://maps.google.com/?cid={place}")
    # unique, stable order
    seen: set[str] = set()
    out: list[str] = []
    for u in uris:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def response_text(response: Any) -> str:
    try:
        return (response.text or "").strip()
    except Exception:  # noqa: BLE001
        parts = []
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    parts.append(part.text)
        return "\n".join(parts).strip()


def inline_bytes(response: Any) -> list[tuple[bytes, str]]:
    blobs: list[tuple[bytes, str]] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                blobs.append((inline.data, inline.mime_type or "application/octet-stream"))
    return blobs


GROUNDING_TOOLS = [
    types.Tool(google_search=types.GoogleSearch()),
    types.Tool(google_maps=types.GoogleMaps()),
    types.Tool(url_context=types.UrlContext()),
]

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""One Indic locale beyond English, from the area of operation. Spec: design.md."""

from __future__ import annotations

from typing import Any

from google.genai import types

from app.engines import gemini_util as g

# (bcp47, english name, script name, native autonym)
_DEFAULT = ("hi-IN", "Hindi", "Devanagari", "हिन्दी")

_STATE_PREFIXES: tuple[tuple[tuple[str, ...], tuple[str, str, str, str]], ...] = (
    (("tamil nadu", "chennai", "coimbatore", "madurai", "trichy"), ("ta-IN", "Tamil", "Tamil", "தமிழ்")),
    (("karnataka", "bengaluru", "bangalore", "mysuru", "mysore"), ("kn-IN", "Kannada", "Kannada", "ಕನ್ನಡ")),
    (("kerala", "kochi", "kozhikode", "thiruvananthapuram"), ("ml-IN", "Malayalam", "Malayalam", "മലയാളം")),
    (("telangana", "hyderabad", "warangal", "andhra", "vijayawada", "visakhapatnam"), ("te-IN", "Telugu", "Telugu", "తెలుగు")),
    (("maharashtra", "mumbai", "pune", "nagpur", "nashik", "thane"), ("mr-IN", "Marathi", "Devanagari", "मराठी")),
    (("gujarat", "ahmedabad", "surat", "vadodara", "rajkot"), ("gu-IN", "Gujarati", "Gujarati", "ગુજરાતી")),
    (("west bengal", "kolkata", "howrah", "siliguri"), ("bn-IN", "Bengali", "Bengali", "বাংলা")),
    (("punjab", "chandigarh", "ludhiana", "amritsar", "mohali"), ("pa-IN", "Punjabi", "Gurmukhi", "ਪੰਜਾਬੀ")),
)


def resolve_locale(geo: str | None) -> dict[str, str]:
    blob = (geo or "").strip().lower()
    picked = _DEFAULT
    for needles, locale in _STATE_PREFIXES:
        if any(n in blob for n in needles):
            picked = locale
            break
    bcp, name, script, native = picked
    return {
        "bcp47": bcp,
        "language": name,
        "script": script,
        "nativeName": native,
        "code": bcp.split("-", 1)[0],
    }


def localize_copy(
    copy: dict[str, Any],
    locale: dict[str, str],
    *,
    business: str,
) -> dict[str, str]:
    """Gemini-native translation into the Indic script. Brand name stays Latin."""
    if not copy or locale.get("code") == "en":
        return {}
    payload = {
        "headline": copy.get("headline") or "",
        "subhead": copy.get("subhead") or "",
        "primaryText": copy.get("primaryText") or "",
        "cta": copy.get("cta") or "",
        "vo": copy.get("voEn") or copy.get("subhead") or "",
        "storyHook": copy.get("storyHook") or "",
    }
    prompt = (
        f"Translate this local-SMB ad copy into {locale.get('language')} "
        f"using {locale.get('script')} script (BCP-47 {locale.get('bcp47')}).\n"
        f"Keep the business name exactly as Latin letters: {business}\n"
        "Do not translate brand names, place names that are commonly Latin "
        "(DLF, Golf Course Road may be kept in Latin), or URLs.\n"
        "Do not add guaranteed/miracle/cure claims that were not in the source.\n"
        "vo must be one spoken sentence, under 22 words, for an 8-second film.\n"
        "Return ONLY JSON with keys: headline, subhead, primaryText, cta, vo, storyHook.\n\n"
        f"SOURCE:\n{payload}"
    )
    try:
        client = g.text_client()
        resp = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        body = g.extract_json(g.response_text(resp))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(body, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("headline", "subhead", "primaryText", "cta", "vo", "storyHook"):
        val = str(body.get(key) or "").strip()
        if val:
            out[key] = val[:500]
    return out


def sanitize_shelf(raw: Any, *, extra_uris: list[str] | None = None) -> list[dict[str, Any]]:
    """Keep structure, drop anything without a public http URI. Never clone pixels."""
    allowed = {"search", "url", "library", "news", "crowd", "maps"}
    rows = raw if isinstance(raw, list) else []
    extras = [u for u in (extra_uris or []) if isinstance(u, str) and u.startswith("http")]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        if not uri.startswith("http") or uri in seen:
            continue
        if _looks_private(uri):
            continue
        seen.add(uri)
        out.append(
            {
                "uri": uri[:500],
                "title": str(item.get("title") or "comparable ad")[:160],
                "snippet": str(item.get("snippet") or "")[:280],
                "hookType": str(item.get("hookType") or "craft")[:48],
                "visualGrammar": str(item.get("visualGrammar") or "")[:80],
                "audioLanguage": str(item.get("audioLanguage") or "")[:40],
                "category": str(item.get("category") or "")[:40],
                "source": str(item.get("source") or "search")[:20]
                if str(item.get("source") or "search") in allowed
                else "search",
            }
        )
        if len(out) >= 8:
            break
    if len(out) < 2:
        for uri in extras:
            if uri in seen or _looks_private(uri):
                continue
            out.append(
                {
                    "uri": uri[:500],
                    "title": "grounded comparable",
                    "snippet": "Cited by Gemini grounding during shelf research.",
                    "hookType": "craft",
                    "visualGrammar": "",
                    "audioLanguage": "",
                    "category": "",
                    "source": "search",
                }
            )
            seen.add(uri)
            if len(out) >= 4:
                break
    return out


def _looks_private(uri: str) -> bool:
    low = uri.lower()
    if low.startswith("mailto:") or "facebook.com/people/" in low:
        return True
    if "/user/" in low or "/in/" in low and "linkedin.com" in low:
        return True
    return False

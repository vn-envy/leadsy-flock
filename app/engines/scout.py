# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Scout — local lens (Maps/Search/urlContext) + crowd lens + BrandSpec."""

from __future__ import annotations

from typing import Any

from google.genai import types

from app.design import resolve_theme
from app.engines import gemini_util as g


SCOUT_PROMPT = """You are Scout, research tracker for a local-SMB growth agency in India.

Return ONLY JSON with this shape:
{{
  "evidence": [
    {{
      "source": "maps" | "search" | "url" | "crowd",
      "uri": "https://...",
      "title": "short title",
      "snippet": "one or two sentences of what you learned",
      "signal": 0.0
    }}
  ],
  "brandSpec": {{
    "themeId": "inkstone" | "ember" | "grove" | "slate" | "paper",
    "palette": ["#hex", "#hex", "#hex"],
    "typePairing": "Georgia + system-ui",
    "toneWords": ["three", "tone", "words"],
    "logoHint": "what the mark looks like if you saw a site, else a guess from the category",
    "tagline": "one line the business could own"
  }},
  "localInsight": "2-3 sentences: competitors, commute, what nearby reviewers praise or complain about",
  "crowdInsight": "category-level pain points from public discussion (Reddit/HN/forums), not private contacts"
}}

Rules:
- Prefer real URIs from grounding. signal is 0-1 (1 = strongly evidenced).
- Do not invent personal emails or phone numbers.
- Discovery is not consent. You research places and public pages, not people to cold-email.
- If a website URL is in the brief, read it with url context.
- themeId must be one of inkstone, ember, grove, slate, paper (see design.md). ember = gyms/energy; grove = wellness; paper = clinics/cafés/salons; slate = professional; inkstone = default. palette hex is for image prompts only — never a CSS background.

Business: {business}
Geo: {geo}
Goal: {goal}
Audience: {audience}
Website: {website}
"""


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    try:
        return _run_inner(campaign)
    except Exception as exc:  # noqa: BLE001
        brief = campaign.get("brief") or {}
        business = brief.get("businessName") or "the business"
        geo = brief.get("geo") or "India"
        return {
            "model": g.TEXT_MODEL,
            "evidence": [],
            "brandSpec": _default_brand(business, geo, brief),
            "localInsight": "",
            "crowdInsight": "",
            "groundingUris": [],
            "errors": [f"{type(exc).__name__}:{exc}"],
        }


def _run_inner(campaign: dict[str, Any]) -> dict[str, Any]:
    brief = campaign.get("brief") or {}
    business = brief.get("businessName") or "the business"
    geo = brief.get("geo") or "India"
    goal = brief.get("goal") or ""
    audience = brief.get("audience") or ""
    website = brief.get("website") or brief.get("site") or ""
    prompt = SCOUT_PROMPT.format(
        business=business,
        geo=geo,
        goal=goal,
        audience=audience,
        website=website or "(none given)",
    )
    client = g.text_client()
    errors: list[str] = []
    response = None
    try:
        response = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=g.GROUNDING_TOOLS,
                temperature=0.3,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"grounded:{type(exc).__name__}:{exc}")
        response = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )

    notes = g.response_text(response)
    uris = g.grounding_uris(response)
    try:
        shaped = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=(
                "Turn these research notes into JSON with keys evidence, brandSpec, "
                "localInsight, crowdInsight. evidence items: source, uri, title, snippet, signal. "
                "Use the URIs listed. Return JSON only.\n\n"
                f"NOTES:\n{notes[:6000]}\n\nURIS:\n{uris}"
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        body = g.extract_json(g.response_text(shaped))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"json:{type(exc).__name__}:{exc}")
        try:
            body = g.extract_json(notes)
        except Exception:
            body = {
                "evidence": [],
                "brandSpec": _default_brand(business, geo, brief),
                "localInsight": notes[:600],
                "parseError": str(exc),
            }

    evidence = list(body.get("evidence") or [])
    for uri in g.grounding_uris(response):
        if not any(e.get("uri") == uri for e in evidence):
            evidence.append(
                {
                    "source": "search" if "maps.google" not in uri else "maps",
                    "uri": uri,
                    "title": "grounding chunk",
                    "snippet": "Cited by Gemini grounding.",
                    "signal": 0.7,
                }
            )
    brand = body.get("brandSpec") or _default_brand(business, geo, brief)
    theme = resolve_theme(brand)
    if isinstance(brand, dict):
        brand = dict(brand)
        brand["themeId"] = theme.id
        brand["palette"] = theme.image_palette
        brand["typePairing"] = "Georgia + system-ui"
    return {
        "model": g.TEXT_MODEL,
        "evidence": evidence[:12],
        "brandSpec": brand,
        "localInsight": body.get("localInsight") or "",
        "crowdInsight": body.get("crowdInsight") or "",
        "groundingUris": g.grounding_uris(response),
        "errors": errors,
    }


def _default_brand(business: str, geo: str, brief: dict[str, Any] | None = None) -> dict[str, Any]:
    brief = brief or {}
    blob = f"{business} {brief.get('goal') or ''} {brief.get('audience') or ''}".lower()
    theme_id = "inkstone"
    if any(w in blob for w in ("gym", "fitness", "crossfit", "workout")):
        theme_id = "ember"
    elif any(w in blob for w in ("salon", "spa", "clinic", "café", "cafe", "bakery")):
        theme_id = "paper"
    elif any(w in blob for w in ("yoga", "wellness", "garden")):
        theme_id = "grove"
    elif any(w in blob for w in ("lawyer", "consultant", "accountant")):
        theme_id = "slate"
    theme = resolve_theme({"themeId": theme_id})
    return {
        "themeId": theme.id,
        "palette": theme.image_palette,
        "typePairing": "Georgia + system-ui",
        "toneWords": ["warm", "direct", "local"],
        "logoHint": f"wordmark for {business}",
        "tagline": f"{business} in {geo}",
    }

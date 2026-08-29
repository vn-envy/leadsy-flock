# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Scout — local lens (Maps/Search/urlContext) + crowd lens + BrandSpec."""

from __future__ import annotations

from typing import Any

from google.genai import types

from app.design import resolve_theme
from app.cost import merge_usage, usage_from_response
from app.engines import gemini_util as g
from app.locale import resolve_locale, sanitize_shelf
from app import own


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
  "crowdInsight": "category-level pain points from public discussion (Reddit/HN/forums), not private contacts",
  "shelf": [
    {{
      "source": "search" | "url" | "library" | "news",
      "uri": "https://...",
      "title": "comparable ad or campaign",
      "snippet": "what structure is working (hook, offer, visual), not a pixel copy",
      "hookType": "anti-influencer" | "after-work" | "price-transparent" | "festive" | "family-trust" | "craft" | "humour",
      "visualGrammar": "quiet interior" | "macro product" | "hands at work" | "humour cut",
      "audioLanguage": "hi" | "en" | "silent",
      "category": "beauty" | "salon" | "jewellery" | "qsr" | "fitness" | "other"
    }}
  ],
  "ownUris": [
    {{
      "uri": "https://...",
      "kind": "website" | "maps" | "listing" | "menu" | "pdf" | "photo",
      "title": "this shop's own page or photo",
      "role": "place" | "proof"
    }}
  ],
  "vertical": "salon" | "food" | "clinic" | "fitness" | "retail" | "other",
  "proofObject": "the thing a stranger must see to book (dish, colour result, SKU, published clinic result)",
  "resolvedName": "the real business name from Maps or the site if the brief name is a placeholder"
}}

Rules:
- Prefer real URIs from grounding. signal is 0-1 (1 = strongly evidenced).
- Do not invent personal emails or phone numbers.
- Discovery is not consent. You research places and public pages, not people to cold-email.
- If a website URL is in the brief, read it with url context.
- ownUris[] is THIS business's own website, Google listing, Maps photos, menu PDF, or shop pictures. Never a competitor. Every item MUST have a real http URI from grounding or the brief. Do not invent photos.
- role=place for interiors/storefronts. role=proof for menu items, plated food, product SKUs, published results. A restaurant without a dish photo is incomplete research.
- vertical names the proof object: food→dish, salon→finished colour, clinic→their published result, fitness→session they can show, retail→SKU.
- If a Google listing or share.google URL is in the brief, open it with url context and Maps. Prefer the listing photos and menu over inventing a shop.
- themeId must be one of inkstone, ember, grove, slate, paper (see design.md). ember = gyms/energy; grove = wellness; paper = clinics/cafés/salons; slate = professional; inkstone = default. palette hex is for image prompts only — never a CSS background.
- shelf[] is comparable ads and campaigns in this category and this city/region that are running or newly discussed THIS season. Use Meta Ad Library, Google Ads Transparency, TikTok Creative Center, Campaign Brief / Social Samosa coverage. Store STRUCTURE (hookType, visualGrammar), never clone a frame. Every shelf item MUST have a real http URI from grounding. Do not scrape private people. Do not invent ads.

Business: {business}
Geo: {geo}
Goal: {goal}
Audience: {audience}
Website: {website}
Listing: {listing}
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
            "shelf": [],
            "ownUris": [],
            "locale": resolve_locale(geo),
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
    listing = brief.get("googleListing") or brief.get("mapsUrl") or ""
    prompt = SCOUT_PROMPT.format(
        business=business,
        geo=geo,
        goal=goal,
        audience=audience,
        website=website or listing or "(none given)",
        listing=listing or website or "(none given)",
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
    shaped = None
    try:
        shaped = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=(
                "Turn these research notes into JSON with keys evidence, brandSpec, "
                "localInsight, crowdInsight, shelf, ownUris, vertical, proofObject, resolvedName. "
                "evidence items: source, uri, title, snippet, signal. "
                "shelf items: source, uri, title, snippet, hookType, visualGrammar, audioLanguage, category. "
                "ownUris items: uri, kind (website|maps|listing|menu|pdf|photo), title, role (place|proof). "
                "vertical is salon|food|clinic|fitness|retail|other. "
                "proofObject is the dish/result/SKU this shop actually shows. "
                "Only use the URIs listed. ownUris must be THIS shop, not a competitor. "
                "Do not invent ads or photos. Return JSON only.\n\n"
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
    out = {
        "model": g.TEXT_MODEL,
        "evidence": evidence[:12],
        "brandSpec": brand,
        "localInsight": body.get("localInsight") or "",
        "crowdInsight": body.get("crowdInsight") or "",
        "shelf": sanitize_shelf(body.get("shelf"), extra_uris=g.grounding_uris(response)),
        "ownUris": own.sanitize_own_uris(
            body.get("ownUris"),
            extra_uris=g.grounding_uris(response),
            website=website or listing,
        ),
        "vertical": body.get("vertical") or "",
        "proofObject": body.get("proofObject") or "",
        "resolvedName": body.get("resolvedName") or "",
        "locale": resolve_locale(geo),
        "groundingUris": g.grounding_uris(response),
        "errors": errors,
    }
    merge_usage(
        out,
        usage_from_response(response, model=g.TEXT_MODEL, kind="text") if response else None,
        usage_from_response(shaped, model=g.TEXT_MODEL, kind="text") if shaped is not None else None,
    )
    return out


def _default_brand(business: str, geo: str, brief: dict[str, Any] | None = None) -> dict[str, Any]:
    brief = brief or {}
    blob = f"{business} {brief.get('goal') or ''} {brief.get('audience') or ''}".lower()
    theme_id = "inkstone"
    if any(w in blob for w in ("gym", "fitness", "crossfit", "workout")):
        theme_id = "ember"
    elif any(w in blob for w in ("salon", "spa", "clinic", "dentist", "café", "cafe", "bakery", "restaurant")):
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

# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Inka — copy + still + Veo clip + Lyria sting, BrandSpec-conditioned."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from google.genai import types

from app import ledger, media, own
from app.derive import derive_images
from app.design import resolve_theme
from app.cost import merge_usage, usage_from_response
from app.engines import gemini_util as g
from app.locale import localize_copy, resolve_locale
from app.vertical import from_scout as vertical_from_scout


COPY_PROMPT = """You are Inka, the artist of a local-SMB agency in India.
Write campaign creative that remixes a CURRENT comparable-ad trope for this shop.
Do not fake UGC. Do not clone another brand's film. Agency/cinematic product craft.
Return ONLY JSON:
{{
  "draftHeadline": "a punchy first-pass line that a junior copywriter might overclaim (include one banned-pattern word like guaranteed/miracle if you would have been tempted)",
  "headline": "compliant headline, no guaranteed outcomes, no medical claims, specific to this business",
  "subhead": "one supporting sentence",
  "primaryText": "2-3 sentences for a Meta primary text, under 125 words",
  "cta": "short CTA",
  "storyHook": "one sentence: winning shelf trope × local pain × this business",
  "voEn": "one ENGLISH spoken sentence, Latin script only, under 18 words, for an 8-second PLACE film, no claims",
  "shotList": "three beats for an 8-second 9:16 PLACE film: this shop's room/station/light — no people, no hands, no faces, no on-screen text",
  "veoPrompt": "English cinematic direction for Veo 3.1, 8 seconds, 9:16, slow push, THIS shop's real interior dead-centre, EMPTY of people, no on-screen text, room tone only",
  "shotListProof": "three beats for a second 8-second 9:16 PROOF film: the thing a stranger must see to book (dish / finished colour / published result / SKU), from THEIR menu or photos, no people unless the photo already is their published result and you keep it as product-still, no on-screen text",
  "veoPromptProof": "English cinematic direction for Veo 3.1, 8 seconds, 9:16, slow push-in on the PROOF object from this shop's own menu/result/SKU photo, EMPTY of invented people, no on-screen text, room tone only",
  "voEnProof": "one ENGLISH spoken sentence under 18 words about the proof object, no claims",
  "imagePrompt": "16:9 still of the PLACE (empty interior), BrandSpec palette, no people, no text",
  "storyPrompt": "9:16 vertical PLACE still, subject in the centre third, BrandSpec palette, no people, no text",
  "detailPrompt": "tight still of the PROOF object (plated dish, colour result, SKU, published clinic result) from this shop, BrandSpec palette, no invented faces, no text",
  "lyriaPrompt": "2-second instrumental sting, no vocals"
}}

Never put a real person's name, email, or phone in the copy.
BrandSpec: {brand}
Shelf tropes (remix structure only): {shelf}
Local insight: {local}
Crowd insight: {crowd}
Evidence (summaries only): {evidence}
Own visual sources (use these rooms/products, do not invent a different shop): {own}
Proof object for this vertical: {proof}
Policy memory from the gate (honor these): {policy}
Locale for spoken line / captions: {locale}
Business: {business} in {geo}. Goal: {goal}. Audience: {audience}.
Attempt: {attempt}
"""


def run(campaign: dict[str, Any]) -> dict[str, Any]:
    try:
        return _run_inner(campaign)
    except Exception as exc:  # noqa: BLE001 — never fail the flock on a media glitch
        brief = campaign.get("brief") or {}
        name = brief.get("businessName") or "the business"
        return {
            "model": g.TEXT_MODEL,
            "copy": {
                "draftHeadline": "Guaranteed transformation this month",
                "headline": f"{name} — evenings that fit your commute",
                "subhead": "Local, honest, no miracle claims.",
                "primaryText": str(brief.get("goal") or "")[:240],
                "cta": "See evening slots",
            },
            "assets": {},
            "locale": resolve_locale(str(brief.get("geo") or "")),
            "errors": [f"{type(exc).__name__}:{exc}"],
        }


def _run_inner(campaign: dict[str, Any]) -> dict[str, Any]:
    brief = campaign.get("brief") or {}
    scout = _scout_payload(campaign["id"]) if campaign.get("id") else {}
    brand = scout.get("brandSpec") or {}
    evidence = scout.get("evidence") or []
    shelf = scout.get("shelf") or []
    locale = scout.get("locale") or resolve_locale(str(brief.get("geo") or ""))
    policy = _policy_lines(campaign.get("id") or "")
    snippets = "; ".join(
        f"{e.get('title')}: {str(e.get('snippet') or '')[:180]}" for e in evidence[:6]
    )
    shelf_bits = "; ".join(
        f"{s.get('hookType')}: {str(s.get('snippet') or s.get('title') or '')[:120]}"
        for s in shelf[:6]
    )
    vert = vertical_from_scout(scout, brief)
    prompt = COPY_PROMPT.format(
        brand=str(brand),
        shelf=(shelf_bits or "none yet").replace("{", "(").replace("}", ")"),
        local=str(scout.get("localInsight") or "none")[:400].replace("{", "(").replace("}", ")"),
        crowd=str(scout.get("crowdInsight") or "none")[:300].replace("{", "(").replace("}", ")"),
        evidence=snippets.replace("{", "(").replace("}", ")") or "none yet",
        own=str([u.get("uri") for u in (scout.get("ownUris") or [])][:6] or brief.get("website") or brief.get("googleListing") or "none given").replace("{", "(").replace("}", ")"),
        proof=f"{vert.get('vertical')}: {vert.get('proofObject')}".replace("{", "(").replace("}", ")"),
        policy=(policy or "none").replace("{", "(").replace("}", ")"),
        locale=f"{locale.get('bcp47')} {locale.get('script')}",
        business=brief.get("businessName") or "the business",
        geo=brief.get("geo") or "",
        goal=brief.get("goal") or "",
        audience=brief.get("audience") or "",
        attempt=campaign.get("inkaRevisions") or 1,
    )
    errors: list[str] = []
    client = g.text_client()
    text_resp = None
    try:
        text_resp = client.models.generate_content(
            model=g.TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8),
        )
        copy = g.extract_json(g.response_text(text_resp))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"copy:{type(exc).__name__}:{exc}")
        copy = None
    if not isinstance(copy, dict):
        copy = {
            "draftHeadline": "Guaranteed transformation this month",
            "headline": f"{brief.get('businessName') or 'Us'} — evenings that fit your commute",
            "subhead": "Local, honest, no miracle claims.",
            "primaryText": str(brief.get("goal") or "")[:240],
            "cta": "See evening slots",
            "storyHook": "Quiet craft after work, not an influencer set.",
            "voEn": "Evenings that fit the commute. No cameras. Just the work.",
            "shotList": "interior → hands at work → still product",
            "veoPrompt": (
                "8-second 9:16 cinematic, locked-off, morning light, this shop's interior dead-centre, "
                "no people, no on-screen text, quiet room tone only."
            ),
            "imagePrompt": "Wide 16:9 still of a calm interior, BrandSpec palette, no text.",
            "storyPrompt": "Vertical 9:16 still of the same interior, subject centred, no text.",
            "detailPrompt": "Tight still of tools or product on a wood table, no faces, no text.",
            "lyriaPrompt": "Short bright ukulele sting, no vocals.",
        }

    localized = localize_copy(copy, locale, business=str(brief.get("businessName") or ""))
    if localized:
        copy["headlineLocalized"] = localized.get("headline")
        copy["subheadLocalized"] = localized.get("subhead")
        copy["primaryTextLocalized"] = localized.get("primaryText")
        copy["ctaLocalized"] = localized.get("cta")
        copy["voIndic"] = localized.get("vo")
        copy["voIndicProof"] = localized.get("voProof")
        copy["storyHookLocalized"] = localized.get("storyHook")
    else:
        errors.append("locale:translate_skipped")

    campaign_id = campaign.get("id") or "campaign"
    assets: dict[str, Any] = {}
    skip_veo = os.environ.get("INKA_SKIP_VEO", "0") == "1"
    skip_still = os.environ.get("INKA_SKIP_STILL", "0") == "1"
    skip_lyria = os.environ.get("INKA_SKIP_LYRIA", "0") == "1"

    ref_blobs: list[tuple[bytes, str]] = []
    proof_blobs: list[tuple[bytes, str]] = []
    own_pack: dict[str, Any] = {"origin": "none", "frames": [], "count": 0}
    if skip_still:
        assets["still"] = {"ok": False, "skipped": True, "model": g.IMAGE_MODEL}
        assets["stillStory"] = {"ok": False, "skipped": True}
        assets["stillDetail"] = {"ok": False, "skipped": True}
    else:
        try:
            own_pack = own.gather(campaign_id, brief, scout)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"own:{type(exc).__name__}:{exc}")
            own_pack = {"origin": "none", "frames": [], "errors": [str(exc)]}
        written = own.apply_to_stills(campaign_id, own_pack) if own_pack.get("frames") else {}
        jobs = (
            ("still", copy.get("imagePrompt") or "Wide 16:9 interior still, no text, no people."),
            (
                "still-story",
                copy.get("storyPrompt")
                or "Vertical 9:16 interior still, subject in the centre third, no text, no people.",
            ),
            (
                "still-detail",
                copy.get("detailPrompt") or "Tight product still, no faces, no text.",
            ),
        )
        err_bags = {stem: [] for stem, _p in jobs}
        need_generate = [stem for stem, _p in jobs if not (written.get(stem) or {}).get("ok")]
        if need_generate:
            # Gemini fills only the missing slots. Full generate only if the shop had no photos.
            with ThreadPoolExecutor(max_workers=3) as pool:
                futs = {
                    stem: pool.submit(_still, campaign_id, prompt_s, brand, stem, err_bags[stem])
                    for stem, prompt_s in jobs
                    if stem in need_generate
                }
                for stem, fut in futs.items():
                    written[stem] = fut.result()
                    written[stem]["origin"] = written[stem].get("origin") or "generated"
        assets["still"] = written.get("still") or {"ok": False}
        assets["stillStory"] = written.get("still-story") or {"ok": False}
        assets["stillDetail"] = written.get("still-detail") or {"ok": False}
        for stem, bag in err_bags.items():
            errors.extend(bag)
        if own_pack.get("errors"):
            errors.extend(str(e) for e in own_pack["errors"][:6])
        origin = "generated"
        if own_pack.get("count") and need_generate:
            origin = "mixed"
        elif own_pack.get("count"):
            origin = "own"
        assets["origin"] = origin
        assets["own"] = {
            "count": own_pack.get("count") or 0,
            "tried": own_pack.get("tried") or [],
            "origin": origin,
        }
        for rec in (assets["still"], assets["stillStory"], assets["stillDetail"]):
            raw = rec.pop("_bytes", None) if isinstance(rec, dict) else None
            if raw:
                role = str(rec.get("role") or "")
                blob = (raw, rec.get("mime") or "image/png")
                if role == "proof" or rec is assets["stillDetail"]:
                    proof_blobs.append(blob)
                else:
                    ref_blobs.append(blob)
        if not ref_blobs and proof_blobs:
            ref_blobs = list(proof_blobs)
        if not proof_blobs and ref_blobs:
            proof_blobs = list(ref_blobs)
        if assets["still"].get("ok"):
            derived = derive_images(campaign_id, "still", prefer={"square", "landscape"})
            assets["stillDerivatives"] = derived
            if not assets["stillStory"].get("ok"):
                extra = derive_images(campaign_id, "still", prefer={"story", "feed"})
                assets["stillStory"] = (extra.get("slots") or {}).get("story") or assets["stillStory"]
                assets["stillFeed"] = (extra.get("slots") or {}).get("feed")
            else:
                extra = derive_images(campaign_id, "still-story", prefer={"story", "feed"})
                if (extra.get("slots") or {}).get("story", {}).get("ok"):
                    assets["stillStory"] = {**assets["stillStory"], **(extra["slots"]["story"])}
                assets["stillFeed"] = (extra.get("slots") or {}).get("feed")
            assets["stillSquare"] = ((assets.get("stillDerivatives") or {}).get("slots") or {}).get("square")
            assets["stillLandscape"] = ((assets.get("stillDerivatives") or {}).get("slots") or {}).get("landscape")
    if skip_veo:
        assets["clip"] = {"ok": False, "skipped": True, "model": g.VEO_MODEL, "note": "INKA_SKIP_VEO=1"}
    else:
        assets["clip"] = _veo_start(
            campaign_id,
            copy.get("veoPrompt") or "",
            errors,
            refs=ref_blobs[:3],
            vo_line="",
        )
        assets["clipProof"] = _veo_start(
            campaign_id,
            copy.get("veoPromptProof") or copy.get("veoPrompt") or "",
            errors,
            refs=(proof_blobs or ref_blobs)[:3],
            vo_line="",
        )
    if skip_lyria:
        assets["jingle"] = {
            "ok": False,
            "skipped": True,
            "pending": False,
            "model": g.LYRIA_MODEL,
            "note": "INKA_SKIP_LYRIA=1",
        }
    else:
        assets["jingle"] = {
            "ok": False,
            "pending": True,
            "model": g.LYRIA_MODEL,
            "note": "Lyria runs on inka_harvest so quota 429 cannot timeout Inka",
        }

    out = {
        "model": g.TEXT_MODEL,
        "copy": {
            "draftHeadline": copy.get("draftHeadline"),
            "headline": copy.get("headline"),
            "subhead": copy.get("subhead"),
            "primaryText": copy.get("primaryText"),
            "cta": copy.get("cta"),
            "storyHook": copy.get("storyHook"),
            "voEn": copy.get("voEn"),
            "voEnProof": copy.get("voEnProof"),
            "headlineLocalized": copy.get("headlineLocalized"),
            "subheadLocalized": copy.get("subheadLocalized"),
            "primaryTextLocalized": copy.get("primaryTextLocalized"),
            "ctaLocalized": copy.get("ctaLocalized"),
            "voIndic": copy.get("voIndic"),
            "voIndicProof": copy.get("voIndicProof"),
            "storyHookLocalized": copy.get("storyHookLocalized"),
            "shotList": copy.get("shotList"),
            "shotListProof": copy.get("shotListProof"),
        },
        "prompts": {
            "veo": copy.get("veoPrompt"),
            "veoProof": copy.get("veoPromptProof"),
            "image": copy.get("imagePrompt"),
            "story": copy.get("storyPrompt"),
            "detail": copy.get("detailPrompt"),
            "lyria": copy.get("lyriaPrompt"),
        },
        "vertical": vert,
        "brandSpec": brand,
        "shelf": shelf,
        "locale": locale,
        "assets": assets,
        "errors": errors,
        "resolvedName": scout.get("resolvedName") or "",
    }
    merge_usage(
        out,
        usage_from_response(text_resp, model=g.TEXT_MODEL, kind="text") if text_resp is not None else None,
    )
    return out


def _scout_payload(campaign_id: str) -> dict[str, Any]:
    row = ledger.get_receipt(campaign_id, "scout") or {}
    return row.get("payload") or {}


def _policy_lines(campaign_id: str) -> str:
    if not campaign_id:
        return ""
    try:
        rows = ledger.list_memories(campaign_id, kind="policy")
    except Exception:  # noqa: BLE001
        return ""
    return " | ".join(str(r.get("text") or "") for r in rows[:8])


def _still(
    campaign_id: str, prompt: str, brand: dict, stem: str, errors: list[str]
) -> dict[str, Any]:
    palette = ", ".join(resolve_theme(brand).image_palette)
    full = f"{prompt}\nColor palette: {palette}. No letters, logos, watermarks, or people."
    attempts = (
        (g.image_client, g.IMAGE_MODEL),
        (g.media_client, g.IMAGE_FALLBACK_MODEL),
    )
    last_error = ""
    for client_fn, model in attempts:
        try:
            client = client_fn()
            resp = client.models.generate_content(
                model=model,
                contents=full,
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
            blobs = g.inline_bytes(resp)
            if not blobs:
                last_error = f"{model}:no_image_bytes"
                continue
            data, mime = blobs[0]
            ext = "png" if "png" in (mime or "") else "jpg"
            filename = f"{stem}.{ext}" if stem == "still" else f"{stem}.png"
            path = media.campaign_path(campaign_id, filename)
            uri = media.put_bytes(path, data, mime)
            return {
                "ok": True,
                "model": model,
                "gcs": uri,
                "bytes": len(data),
                "mime": mime,
                "publicPath": f"/media/{campaign_id}/{stem}",
                "_bytes": data,
            }
        except Exception as extra:  # noqa: BLE001
            last_error = f"{model}:{type(extra).__name__}:{extra}"
            continue
    errors.append(f"{stem}:{last_error}")
    return {"ok": False, "model": g.IMAGE_MODEL, "error": last_error[:300]}


def _call_timeout(fn, seconds: int, fallback: Any) -> Any:
    """Time-box a Vertex call without blocking shutdown on the leftover thread."""
    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(fn)
    try:
        return fut.result(timeout=seconds)
    except FuturesTimeout:
        if isinstance(fallback, dict):
            out = dict(fallback)
            out["error"] = f"timeout_{seconds}s"
            return out
        return fallback
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _veo_start(
    campaign_id: str,
    prompt: str,
    errors: list[str],
    *,
    refs: list[tuple[bytes, str]] | None = None,
    vo_line: str = "",
    sequence: tuple[tuple[bool, str], ...] | None = None,
) -> dict[str, Any]:
    """Kick off 8s 9:16 Veo with native audio. Never wait on the LRO."""
    t0 = time.time()
    spoken = " ".join((vo_line or "").split())[:180]
    body = prompt or (
        "8-second 9:16 cinematic interior, morning light, product dead-centre, "
        "empty of people, no on-screen text."
    )
    body = (
        f"{body}\nEmpty of people: no humans, no faces, no hands, no body parts, "
        "no mannequins. Product, tools, and room only."
    )
    if spoken:
        body = (
            f"{body}\nOff-camera spoken dialogue, one line only, in the local language: \"{spoken}\"\n"
            "No burned-in captions or subtitles. Quiet room tone under the line. No on-screen speaker."
        )
    ref_images = []
    for data, mime in (refs or [])[:3]:
        try:
            ref_images.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(image_bytes=data, mime_type=mime or "image/png"),
                    reference_type=types.VideoGenerationReferenceType.ASSET,
                )
            )
        except Exception:  # noqa: BLE001
            continue

    def _start(use_refs: bool, aspect: str) -> Any:
        cfg: dict[str, Any] = {
            "number_of_videos": 1,
            "duration_seconds": 8,
            "aspect_ratio": aspect,
            "generate_audio": True,
            "person_generation": "dont_allow",
            "negative_prompt": (
                "people, person, human, crowd, face, faces, hands, body, skin, "
                "mannequin, celebrity lookalikes, children, minors, "
                "on-screen text, captions, subtitles, logos, watermarks"
            ),
        }
        if use_refs and ref_images:
            cfg["reference_images"] = ref_images
        client = g.media_client()
        return client.models.generate_videos(
            model=g.VEO_MODEL,
            prompt=body,
            config=types.GenerateVideosConfig(**cfg),
        )

    last_error = ""
    steps = sequence or ((True, "9:16"), (False, "9:16"), (False, "16:9"))
    for use_refs, aspect in steps:
        if use_refs and not ref_images:
            continue
        try:
            operation = _start(use_refs, aspect)
            if getattr(operation, "done", False):
                resp = getattr(operation, "response", None) or getattr(operation, "result", None)
                videos = getattr(resp, "generated_videos", None) if resp else None
                reasons = list(getattr(resp, "rai_media_filtered_reasons", None) or []) if resp else []
                if not videos:
                    last_error = (
                        f"{aspect}:{'refs' if use_refs else 'plain'}:"
                        f"rai:{'; '.join(reasons) or 'done_empty'}"
                    )
                    continue
            return {
                "ok": True,
                "model": g.VEO_MODEL,
                "status": "started" if not getattr(operation, "done", False) else "done",
                "operation": getattr(operation, "name", None),
                "seconds": round(time.time() - t0, 1),
                "campaignId": campaign_id,
                "durationSeconds": 8,
                "aspectRatio": aspect,
                "generateAudio": True,
                "usedRefs": bool(use_refs and ref_images),
            }
        except Exception as exc:  # noqa: BLE001
            last_error = f"{aspect}:{'refs' if use_refs else 'plain'}:{type(exc).__name__}:{exc}"
            continue
    errors.append(f"veo:{last_error}")
    return {"ok": False, "model": g.VEO_MODEL, "error": last_error[:300]}


def _lyria(campaign_id: str, prompt: str, errors: list[str]) -> dict[str, Any]:
    try:
        client = g.media_client()
        resp = client.models.generate_content(
            model=g.LYRIA_MODEL,
            contents=prompt or "A 2-second bright instrumental sting, no vocals.",
            config=types.GenerateContentConfig(response_modalities=["AUDIO"]),
        )
        blobs = g.inline_bytes(resp)
        if not blobs:
            errors.append("lyria:no_audio")
            return {"ok": False, "model": g.LYRIA_MODEL}
        data, mime = blobs[0]
        ext = "wav" if "wav" in (mime or "") else "bin"
        uri = media.put_bytes(media.campaign_path(campaign_id, f"jingle.{ext}"), data, mime)
        return {
            "ok": True,
            "model": g.LYRIA_MODEL,
            "gcs": uri,
            "bytes": len(data),
            "mime": mime,
            "publicPath": f"/media/{campaign_id}/jingle",
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"lyria:{type(exc).__name__}:{exc}")
        return {"ok": False, "model": g.LYRIA_MODEL, "error": str(exc)[:300], "quotaLikely": "429" in str(exc)}

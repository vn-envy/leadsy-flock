# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Model Armor boundary screening. Fail-closed on transport errors."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import google.auth
from google.auth.transport.requests import Request

from app.settings import load_settings


class ArmorBlocked(Exception):
    def __init__(self, verdict: dict):
        super().__init__("model armor blocked inbound text")
        self.verdict = verdict


def _access_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid:
        creds.refresh(Request())
    if not creds.token:
        creds.refresh(Request())
    return creds.token  # type: ignore[return-value]


def sanitize_user_prompt(text: str) -> dict:
    """Screen inbound owner text. Returns the Model Armor JSON; raises ArmorBlocked if blocked."""
    settings = load_settings()
    if not settings.project_id:
        return {"skipped": True, "reason": "no_project"}
    loc = settings.armor_location
    name = (
        f"projects/{settings.project_id}/locations/{loc}/templates/{settings.armor_template}"
    )
    url = (
        f"https://modelarmor.{loc}.rep.googleapis.com/v1/{name}:sanitizeUserPrompt"
    )
    payload = json.dumps({"userPromptData": {"text": text}}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise ArmorBlocked(
            {
                "blocked": True,
                "failClosed": True,
                "http": exc.code,
                "error": err[:500],
            }
        ) from exc

    sanitization = body.get("sanitizationResult") or body
    filter_results = sanitization.get("filterResults") or {}
    # MATCH_FOUND / BLOCKED across RAI / PI filters.
    blocked = False
    if sanitization.get("filterMatchState") == "MATCH_FOUND":
        blocked = True
    if str(sanitization.get("sanitizationResult") or "").upper() in {
        "SANITIZATION_RESULT_BLOCKED",
        "BLOCKED",
    }:
        blocked = True
    verdict = {
        "blocked": blocked,
        "template": name,
        "raw": body,
        "filterResults": filter_results,
    }
    if blocked:
        raise ArmorBlocked(verdict)
    return verdict

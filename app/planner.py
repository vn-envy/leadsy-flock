# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Deterministic Bri v1 — catalog in, recommended flock out. No LLM required."""

from __future__ import annotations

from app.flock import FLOCK

# India launch prices, rupees, per campaign. Static config — not checkout.
ENGINE_PRICE_INR = {
    "scout": 1999,
    "inka": 2499,
    "stella": 1499,
    "ray": 1999,
    "callie": 3499,
}

BUNDLE_LAUNCH = ("scout", "inka", "stella")
BUNDLE_FIND = ("scout",)
BUNDLE_FULL = ("scout", "inka", "stella", "ray")


def recommend_flock(
    *,
    goal: str = "",
    budget_inr: int | None = None,
    include_outreach: bool = False,
) -> dict:
    """Pick engines from the catalog. Always-on birds are free and always included."""
    goal_l = (goal or "").lower()
    if include_outreach or "email" in goal_l or "whatsapp" in goal_l:
        hired = list(BUNDLE_FULL)
    elif budget_inr is not None and budget_inr < 4000:
        hired = list(BUNDLE_FIND)
    else:
        hired = list(BUNDLE_LAUNCH)

    hired = [e for e in hired if _is_hireable(e)]
    if budget_inr is not None:
        hired = _fit_budget(hired, budget_inr)

    always = [b.id for b in FLOCK if b.always_on]
    total = sum(ENGINE_PRICE_INR.get(e, 0) for e in hired)
    rationale = []
    if "scout" in hired:
        rationale.append("Scout first: local evidence before any creative.")
    if "inka" in hired:
        rationale.append("Inka + Stella: one gated master creative and a consent page.")
    if "ray" in hired:
        rationale.append("Ray only after a consent record exists — discovery ≠ consent.")
    if "callie" not in hired:
        rationale.append("Callie is listed but not hired for this hackathon run.")

    return {
        "always_on": always,
        "hired": hired,
        "pipeline": _pipeline(hired),
        "price_inr": total,
        "currency": "INR",
        "rationale": rationale,
        "accepted_recommendation": True,
    }


def _is_hireable(engine_id: str) -> bool:
    bird = next((b for b in FLOCK if b.id == engine_id), None)
    return bool(bird and bird.hired_in_hackathon_run and not bird.always_on)


def _fit_budget(hired: list[str], budget: int) -> list[str]:
    drop_order = ["ray", "stella", "inka", "scout"]
    selected = list(hired)
    while selected and sum(ENGINE_PRICE_INR.get(e, 0) for e in selected) > budget:
        for drop in drop_order:
            if drop in selected:
                selected.remove(drop)
                break
        else:
            break
    return selected


def _pipeline(hired: list[str]) -> list[str]:
    """Ordered worker steps. Ledger gates always run when the producing engine is hired."""
    steps: list[str] = []
    if "scout" in hired:
        steps.append("scout")
    if "inka" in hired:
        steps.extend(["inka", "creative_gate"])
    if "stella" in hired:
        steps.append("stella")
    if "inka" in hired and "stella" in hired:
        steps.append("ad_kit")
    if "ray" in hired:
        steps.append("outreach_gate")
        steps.append("ray")
    if not steps:
        steps = ["scout"]
    return steps

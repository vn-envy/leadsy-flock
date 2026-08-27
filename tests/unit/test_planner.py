# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.planner import ENGINE_PRICE_INR, recommend_flock


def test_default_is_launch_bundle() -> None:
    rec = recommend_flock(goal="Grow evening memberships at a gym in Gurgaon.")
    assert rec["hired"] == ["scout", "inka", "stella"]
    assert rec["pipeline"] == ["scout", "inka", "creative_gate", "stella", "ad_kit"]
    assert rec["price_inr"] == sum(ENGINE_PRICE_INR[e] for e in rec["hired"])
    assert rec["currency"] == "INR"
    assert "flo" in rec["always_on"]
    assert "bri" in rec["always_on"]
    assert "ledge" in rec["always_on"]


def test_tight_budget_is_find_bundle() -> None:
    rec = recommend_flock(goal="Find local customers.", budget_inr=2500)
    assert rec["hired"] == ["scout"]
    assert rec["pipeline"] == ["scout"]
    assert rec["price_inr"] == ENGINE_PRICE_INR["scout"]


def test_outreach_goal_adds_ray_and_outreach_gate() -> None:
    rec = recommend_flock(
        goal="Find 30 SaaS founders in Mumbai and email them.",
        include_outreach=True,
    )
    assert rec["hired"] == ["scout", "inka", "stella", "ray"]
    assert rec["pipeline"][-1] == "outreach_gate"
    assert "ad_kit" in rec["pipeline"]
    assert rec["price_inr"] == sum(ENGINE_PRICE_INR[e] for e in rec["hired"])


def test_callie_is_never_hired() -> None:
    rec = recommend_flock(goal="I want voice calling and email and ads.")
    assert "callie" not in rec["hired"]

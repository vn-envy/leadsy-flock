# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.engines import adkit, gate, inka, outreach, scout, stella


def dispatch(step: str, campaign: dict) -> dict:
    if step == "scout":
        return scout.run(campaign)
    if step == "inka":
        return inka.run(campaign)
    if step == "creative_gate":
        return gate.run(campaign)
    if step == "stella":
        return stella.run(campaign)
    if step == "ad_kit":
        return adkit.run(campaign)
    if step == "outreach_gate":
        return outreach.run_gate(campaign)
    if step == "ray":
        return outreach.run_ray(campaign)
    return {"note": f"unknown step {step} recorded"}

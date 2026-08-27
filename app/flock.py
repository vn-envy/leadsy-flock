# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Canonical Flock roster for day-1 Hello Flo.

Typed catalog only — no execution. Specialist engines join the Pub/Sub
worker on later days. Keeping this as data (not a prompt dump) is what
lets Bri select a team against a catalog instead of a hardcoded speech.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Bird:
    id: str
    name: str
    role: str
    engine: str
    always_on: bool
    hired_in_hackathon_run: bool
    contract: str

    def as_dict(self) -> dict:
        return asdict(self)


FLOCK: tuple[Bird, ...] = (
    Bird(
        id="flo",
        name="Flo",
        role="Director",
        engine="flo",
        always_on=True,
        hired_in_hackathon_run=True,
        contract="Freeform owner message → structured brief + plan approval.",
    ),
    Bird(
        id="bri",
        name="Bri",
        role="Strategist",
        engine="brain",
        always_on=True,
        hired_in_hackathon_run=True,
        contract="Brief + catalog → recommended flock, price, rationale.",
    ),
    Bird(
        id="scout",
        name="Scout",
        role="Tracker",
        engine="scout",
        always_on=False,
        hired_in_hackathon_run=True,
        contract="Brief → evidence[] with source URIs (Maps, Search, crowd).",
    ),
    Bird(
        id="inka",
        name="Inka",
        role="Artist",
        engine="studio",
        always_on=False,
        hired_in_hackathon_run=True,
        contract="Evidence + BrandSpec → copy, stills, Veo clip, Lyria track.",
    ),
    Bird(
        id="stella",
        name="Stella",
        role="Host",
        engine="stage",
        always_on=False,
        hired_in_hackathon_run=True,
        contract="LandingSpec → published page with consent-first capture.",
    ),
    Bird(
        id="ray",
        name="Ray",
        role="Postbird",
        engine="reach",
        always_on=False,
        hired_in_hackathon_run=True,
        contract="Consented lead → sandboxed email. No consent = refuse.",
    ),
    Bird(
        id="callie",
        name="Callie",
        role="Voice",
        engine="closer",
        always_on=False,
        hired_in_hackathon_run=False,
        contract="Not hired for this hackathon run.",
    ),
    Bird(
        id="ledge",
        name="Ledge",
        role="Auditor",
        engine="ledger",
        always_on=True,
        hired_in_hackathon_run=True,
        contract="Every action → receipt + gate verdict. Fail-closed.",
    ),
)


def describe_flock() -> str:
    lines = []
    for bird in FLOCK:
        flag = "always on" if bird.always_on else "hired per campaign"
        hired = "in this run" if bird.hired_in_hackathon_run else "not hired this run"
        lines.append(f"{bird.name} ({bird.role}) — {flag}; {hired}. {bird.contract}")
    return "\n".join(lines)

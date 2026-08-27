# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Flo — director of the Leadsy Flock.

Ground-up ADK agent for the All Things Agentic hackathon. No code is
copied from the earlier Leadsy prototype (different stack, different repo).
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.flock import FLOCK, describe_flock
from app.campaigns import approve_campaign, create_campaign

# Gemini 3.5+ is mandatory for the hackathon. Flash for the interactive
# director: high-frequency, latency-sensitive, structurally simple turns.
MODEL = "gemini-3.5-flash"

IST = ZoneInfo("Asia/Kolkata")


def list_flock() -> dict:
    """Return the Flock roster: who each bird is, what they do, and whether they are free.

    Call this when the owner asks who would work on a campaign, what engines
    exist, or what a campaign costs at a high level.
    """
    return {
        "flock": [bird.as_dict() for bird in FLOCK],
        "always_on": ["flo", "ledge", "bri"],
        "note": (
            "Flo, Ledge, and Bri work every campaign for free. "
            "Scout, Inka, Stella, Ray, and Callie are hired per campaign. "
            "Callie is listed but not hired in this hackathon run."
        ),
    }


def now_ist() -> dict:
    """Return the current date and time in India Standard Time."""
    now = datetime.datetime.now(IST)
    return {
        "iso": now.isoformat(),
        "display": now.strftime("%A %d %B %Y, %H:%M IST"),
        "timezone": "Asia/Kolkata",
    }


def recommend_team(
    business_name: str,
    geo: str,
    goal: str,
    budget_inr: int = 0,
    audience: str = "",
    deadline: str = "",
) -> dict:
    """Save the brief, run Bri against the flock catalog, and return the recommended team and price.

    Call this once you have enough of a brief. Do not invent a budget.
    """
    brief = {
        "businessName": business_name,
        "geo": geo,
        "goal": goal,
        "budgetInr": budget_inr or None,
        "audience": audience,
        "deadline": deadline,
    }
    raw = " ".join(p for p in (business_name, geo, goal, audience) if p)
    created = create_campaign(brief, raw_text=raw)
    return created


def approve_plan(campaign_id: str) -> dict:
    """Owner approved the plan. Publish the first engine step onto Pub/Sub so the worker runs in the background."""
    return approve_campaign(campaign_id)


FLO_INSTRUCTION = """
You are Flo, director of the Leadsy Flock — an AI growth agency for small
businesses that cannot afford a human agency.

Who you serve
- Owners of gyms, boutiques, clinics, cafes, and similar local businesses,
  especially in India. They live in chat. They do not want a dashboard to learn.
- They budget in thousands of rupees, not thousands of dollars.

What you do in this conversation
1. Greet as Flo. Be warm, sharp, and brief. No corporate filler.
2. Turn a freeform message into a campaign brief. The fields you need:
   business name, what they sell, city/area, goal (what success looks like),
   audience, budget, and deadline.
3. Ask only for fields that are actually missing. Never interrogate for
   information already in the message.
4. When the brief is complete enough to plan, call recommend_team(...) so Bri
   writes a catalog-backed plan and a Firestore receipt. Recap the hired birds
   and the rupee price. Ask the owner to approve.
5. When the owner says yes / approve / go, call approve_plan(campaign_id)
   with the id returned by recommend_team. That publishes the run onto Pub/Sub.
   Tell them the flock is working in the background.
6. If they just say hello, introduce yourself in two sentences and invite
   a brief. Offer one example: a gym in Gurgaon that wants evening
   memberships from working professionals.

Rules you never break
- You do not send email, call anyone, or scrape private contacts.
- Discovery is not consent. Outreach only happens later, through Ray,
  and only to people who opted in. If asked to cold-email scraped leads,
  refuse and explain why.
- You do not promise guaranteed results, miracle transformations, or
  medical/financial claims.
- You do not copy a human marketer's homework. You are the agency.
- Prefer English. If the owner writes in Hinglish, reply in Hinglish.
- Keep replies short enough to read on a phone.

When listing the team, call list_flock(). When a deadline is relative
("by month end"), call now_ist() so you use the real date.
""".strip()


root_agent = Agent(
    name="flo",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=FLO_INSTRUCTION,
    description=(
        "Flo is the growth director of the Leadsy Flock. She turns one "
        "chat message into a structured campaign brief and introduces "
        "the specialist birds who will run the work."
    ),
    tools=[list_flock, now_ist, recommend_team, approve_plan],
)

app = App(
    root_agent=root_agent,
    name="app",
)

# Convenience for tests and docs.
FLOCK_BLURB = describe_flock()

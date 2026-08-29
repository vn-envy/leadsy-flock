# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Per-request channel context (Telegram chat, studio). Tools read this."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass
class ChannelCtx:
    source: str = "web"
    chat_id: int | str | None = None
    user_id: int | str | None = None
    campaign_id: str | None = None


CURRENT: ContextVar[ChannelCtx | None] = ContextVar("flock_channel", default=None)


def get() -> ChannelCtx | None:
    return CURRENT.get()


def bind(ctx: ChannelCtx):
    return CURRENT.set(ctx)


def reset(token: Any) -> None:
    CURRENT.reset(token)


def stamp_campaign(campaign_id: str) -> None:
    ctx = CURRENT.get()
    if ctx is not None:
        ctx.campaign_id = campaign_id

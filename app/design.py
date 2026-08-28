# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Validated landing tokens. Spec: design.md. Stella must not paint unchecked hex."""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from typing import Any

AA_BODY = 4.5
AA_UI = 3.0
AAA_BODY = 7.0

_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class Theme:
    id: str
    bg: str
    fg: str
    muted: str
    accent: str
    accent_fg: str
    surface: str
    line: str
    scheme: str  # "dark" | "light"

    @property
    def image_palette(self) -> list[str]:
        return [self.accent, self.bg, self.fg]

    def css_vars(self) -> str:
        return (
            f"--bg:{self.bg};--fg:{self.fg};--muted:{self.muted};"
            f"--accent:{self.accent};--accent-fg:{self.accent_fg};"
            f"--surface:{self.surface};--line:{self.line};"
        )


THEMES: dict[str, Theme] = {
    "inkstone": Theme(
        id="inkstone",
        bg="#14181f",
        fg="#f3eee6",
        muted="#b7aea2",
        accent="#c4a574",
        accent_fg="#14181f",
        surface="#1c222c",
        line="#2c3340",
        scheme="dark",
    ),
    "ember": Theme(
        id="ember",
        bg="#16120f",
        fg="#f6efe8",
        muted="#c4b6a8",
        accent="#e08a4a",
        accent_fg="#16120f",
        surface="#221c18",
        line="#3a322c",
        scheme="dark",
    ),
    "grove": Theme(
        id="grove",
        bg="#101510",
        fg="#eaf0e8",
        muted="#a9b5a8",
        accent="#c4b07a",
        accent_fg="#101510",
        surface="#181e18",
        line="#2a332a",
        scheme="dark",
    ),
    "slate": Theme(
        id="slate",
        bg="#10161c",
        fg="#e8eef3",
        muted="#9aa8b4",
        accent="#7eaebe",
        accent_fg="#10161c",
        surface="#171e26",
        line="#2a3540",
        scheme="dark",
    ),
    "paper": Theme(
        id="paper",
        bg="#f7f1e8",
        fg="#1c1814",
        muted="#5e574e",
        accent="#8b5a2b",
        accent_fg="#f7f1e8",
        surface="#fffdf8",
        line="#ddd4c6",
        scheme="light",
    ),
}

DEFAULT_THEME_ID = "inkstone"


def resolve_theme(brand: dict[str, Any] | None) -> Theme:
    brand = brand or {}
    named = str(brand.get("themeId") or brand.get("theme") or "").strip().lower()
    if named in THEMES:
        base = THEMES[named]
    else:
        base = THEMES[_infer_theme_id(brand.get("palette") or [])]
    accent = _safe_accent(brand.get("palette") or [], base)
    if accent == base.accent:
        return base
    return Theme(
        id=base.id,
        bg=base.bg,
        fg=base.fg,
        muted=base.muted,
        accent=accent,
        accent_fg=base.accent_fg,
        surface=base.surface,
        line=base.line,
        scheme=base.scheme,
    )


def _infer_theme_id(palette: list[Any]) -> str:
    parsed = [_parse_hex(c) for c in palette]
    colors = [c for c in parsed if c]
    if not colors:
        return DEFAULT_THEME_ID
    if any(_is_light(c) for c in colors) and not any(_is_dark(c) for c in colors):
        return "paper"
    hues = [_hue_sat(c) for c in colors]
    if any(8 <= h <= 45 and s >= 0.4 for h, s in hues):
        return "ember"
    if any(90 <= h <= 160 and s >= 0.25 for h, s in hues):
        return "grove"
    if any(185 <= h <= 250 and s >= 0.25 for h, s in hues):
        return "slate"
    return DEFAULT_THEME_ID


def _safe_accent(palette: list[Any], base: Theme) -> str:
    for raw in palette:
        hex_color = _normalize_hex(raw)
        if not hex_color:
            continue
        if contrast(hex_color, base.bg) < AA_UI:
            continue
        if contrast(base.accent_fg, hex_color) < AA_BODY:
            continue
        # Accent must not collapse into the canvas (the Peak Gym failure mode).
        if contrast(hex_color, base.bg) < 2.5:
            continue
        if _rel_luminance(hex_color) < 0.12 and base.scheme == "dark":
            continue
        return hex_color
    return base.accent


def contrast(a: str, b: str) -> float:
    l1 = _rel_luminance(a)
    l2 = _rel_luminance(b)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def assert_readable(theme: Theme) -> None:
    if contrast(theme.fg, theme.bg) < AAA_BODY:
        raise ValueError(f"{theme.id}: fg/bg contrast {contrast(theme.fg, theme.bg):.2f} < {AAA_BODY}")
    if contrast(theme.muted, theme.bg) < AA_BODY:
        raise ValueError(f"{theme.id}: muted/bg contrast {contrast(theme.muted, theme.bg):.2f} < {AA_BODY}")
    if contrast(theme.accent, theme.bg) < AA_UI:
        raise ValueError(f"{theme.id}: accent/bg contrast {contrast(theme.accent, theme.bg):.2f} < {AA_UI}")
    if contrast(theme.accent_fg, theme.accent) < AA_BODY:
        raise ValueError(
            f"{theme.id}: accent-fg/accent contrast {contrast(theme.accent_fg, theme.accent):.2f} < {AA_BODY}"
        )


def _parse_hex(value: Any) -> tuple[int, int, int] | None:
    text = _normalize_hex(value)
    if not text:
        return None
    return int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16)


def _normalize_hex(value: Any) -> str | None:
    text = str(value or "").strip()
    if not _HEX.match(text):
        return None
    if not text.startswith("#"):
        text = "#" + text
    return text.lower()


def _rel_luminance(hex_color: str) -> float:
    rgb = _parse_hex(hex_color)
    if not rgb:
        return 0.0

    def to_lin(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (to_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _is_light(rgb: tuple[int, int, int]) -> bool:
    return _rel_luminance(_rgb_hex(rgb)) >= 0.7


def _is_dark(rgb: tuple[int, int, int]) -> bool:
    return _rel_luminance(_rgb_hex(rgb)) <= 0.12


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _hue_sat(rgb: tuple[int, int, int]) -> tuple[float, float]:
    r, g, b = (c / 255.0 for c in rgb)
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0, s

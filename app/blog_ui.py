# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Public blog — written for Google's All Things Agentic hackathon."""

from __future__ import annotations

import html
import re
from pathlib import Path

from app.run_ui import ASSET, _cast_html, _src

_CANDIDATES = (
    Path(__file__).resolve().parent / "blog.md",
    Path(__file__).resolve().parents[1] / "docs" / "blog.md",
)
POST = next((p for p in _CANDIDATES if p.is_file()), _CANDIDATES[0])


def render_html() -> str:
    return render_post(
        POST,
        kicker="All Things Agentic · August 2026",
        here="blog",
        md_href="/blog.md",
    )


def render_post(
    source: Path,
    *,
    kicker: str,
    here: str,
    md_href: str,
) -> str:
    raw = source.read_text(encoding="utf-8") if source.is_file() else ""
    title, body = _split_title(raw)
    hero = _src("hero")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} · Leadsy Flock</title>
  <link rel="stylesheet" href="{ASSET}/dash.css?v=blog"/>
  <style>
    .post {{
      max-width: 40rem;
      margin: .2rem auto 0;
      color: var(--ink);
      line-height: 1.6;
      font-size: 1.02rem;
    }}
    .post .kicker {{
      font-size: .68rem; letter-spacing: .16em; text-transform: uppercase; color: var(--ash);
      margin: 0 0 .45rem;
    }}
    .post h1 {{
      font-size: clamp(1.7rem, 4vw, 2.45rem);
      line-height: 1.12;
      margin: 0 0 .7rem;
    }}
    .post .standfirst {{
      color: var(--ash); font-size: .98rem; line-height: 1.5; margin: 0 0 1.2rem;
    }}
    .post h2 {{
      font-family: Palatino, "Palatino Linotype", Georgia, serif;
      font-weight: 500;
      font-size: 1.28rem;
      margin: 1.6rem 0 .5rem;
      color: var(--ink);
    }}
    .post h3 {{
      font-size: 1.02rem;
      font-weight: 600;
      margin: 1.2rem 0 .4rem;
    }}
    .post p {{ margin: 0 0 .85rem; }}
    .post ol, .post ul {{ margin: 0 0 1rem; padding-left: 1.2rem; }}
    .post li {{ margin: 0 0 .4rem; }}
    .post em {{ color: var(--silt); }}
    .post blockquote {{
      margin: 0 0 1rem;
      padding: .15rem 0 .15rem .9rem;
      border-left: 3px solid var(--pink, #d49a9a);
      color: var(--silt);
    }}
    .post hr {{
      border: 0; border-top: 1px solid var(--line); margin: 1.4rem 0;
    }}
    .post table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .88rem;
      margin: 0 0 1rem;
    }}
    .post th, .post td {{
      text-align: left;
      vertical-align: top;
      padding: .45rem .5rem;
      border-bottom: 1px solid var(--line);
    }}
    .post th {{ color: var(--ash); font-weight: 500; }}
    .post .arch {{
      margin: .4rem 0 1.1rem;
      border-radius: 1.1rem;
      border: 1px solid var(--line);
      background: var(--paper);
      overflow: hidden;
    }}
    .post .arch img {{ display: block; width: 100%; height: auto; }}
  </style>
</head>
<body>
<section class="wash" style="background-image:url('{hero}')">
  <div class="grain" aria-hidden="true"></div>
  <div class="veil"></div>
  <div class="cast">{_cast_html()}</div>
</section>
<main class="sheet">
  <header class="mast">
    <a class="word" href="/demo">Leadsy Flock</a>
    <nav>
      <a href="/demo">roost</a>
      <a href="/dash">observatory</a>
      <a href="/trace">backend path</a>
      <a href="/architecture">architecture</a>
      <span class="here">{html.escape(here)}</span>
    </nav>
  </header>
  <article class="post">
    <p class="kicker">{html.escape(kicker)}</p>
    <h1>{html.escape(title)}</h1>
    {_article_html(body)}
  </article>
  <p class="note">This article was created for the purposes of entering Google's All Things Agentic hackathon. Markdown: <a href="{html.escape(md_href)}">{html.escape(md_href)}</a>. We do not autopost.</p>
</main>
</body>
</html>
"""


def _split_title(raw: str) -> tuple[str, str]:
    lines = raw.strip().splitlines()
    title = "Leadsy Flock"
    rest: list[str] = []
    started = False
    for line in lines:
        if not started and line.startswith("# "):
            title = line[2:].strip()
            started = True
            continue
        if started:
            rest.append(line)
        elif line.strip():
            rest.append(line)
            started = True
    return title, "\n".join(rest).strip()


def _article_html(md: str) -> str:
    chunks: list[str] = []
    para: list[str] = []
    list_kind = ""
    items: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if not para:
            return
        text = " ".join(para)
        if text.startswith("*") and text.endswith("*") and not text.startswith("**"):
            chunks.append(f'<p class="standfirst">{_inline(text.strip("*").strip())}</p>')
        else:
            chunks.append(f"<p>{_inline(text)}</p>")
        para = []

    def flush_list() -> None:
        nonlocal list_kind, items
        if not items:
            return
        tag = "ol" if list_kind == "ol" else "ul"
        inner = "".join(f"<li>{_inline(x)}</li>" for x in items)
        chunks.append(f"<{tag}>{inner}</{tag}>")
        items = []
        list_kind = ""

    image = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)$')
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        head, *body = table_rows
        def cells(row: list[str], tag: str) -> str:
            return "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in row)
        thead = f"<thead><tr>{cells(head, 'th')}</tr></thead>"
        tbody = "<tbody>" + "".join(f"<tr>{cells(r, 'td')}</tr>" for r in body) + "</tbody>"
        chunks.append(f"<table>{thead}{tbody}</table>")
        table_rows = []

    def table_row(line: str) -> list[str] | None:
        raw = line.strip()
        if not raw.startswith("|"):
            return None
        bits = [c.strip() for c in raw.strip("|").split("|")]
        if bits and all(set(c) <= set("-: ") and c for c in bits):
            return []
        return bits

    for line in md.splitlines():
        numbered = re.match(r"^(\d+)\.\s+(.*)$", line)
        bullet = re.match(r"^-\s+(.*)$", line)
        pic = image.match(line.strip())
        row = table_row(line)
        quote = re.match(r"^>\s?(.*)$", line)
        if row is not None:
            flush_para()
            flush_list()
            if row:
                table_rows.append(row)
            continue
        flush_table()
        if line.strip() in {"---", "***", "***"}:
            flush_para()
            flush_list()
            chunks.append("<hr/>")
        elif line.startswith("### "):
            flush_para()
            flush_list()
            chunks.append(f"<h3>{_inline(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            flush_para()
            flush_list()
            chunks.append(f"<h2>{_inline(line[3:].strip())}</h2>")
        elif quote:
            flush_para()
            flush_list()
            chunks.append(f"<blockquote><p>{_inline(quote.group(1))}</p></blockquote>")
        elif pic:
            flush_para()
            flush_list()
            alt = html.escape(pic.group(1))
            src = html.escape(pic.group(2), quote=True)
            chunks.append(f'<figure class="arch"><img src="{src}" alt="{alt}"/></figure>')
        elif numbered:
            flush_para()
            if list_kind != "ol":
                flush_list()
                list_kind = "ol"
            items.append(numbered.group(2))
        elif bullet:
            flush_para()
            if list_kind != "ul":
                flush_list()
                list_kind = "ul"
            items.append(bullet.group(1))
        elif not line.strip():
            flush_para()
            flush_list()
        else:
            flush_list()
            para.append(line.strip())
    flush_para()
    flush_list()
    flush_table()
    return "\n".join(chunks)


def _inline(text: str) -> str:
    parts: list[str] = []
    idx = 0
    pattern = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*")
    for match in pattern.finditer(text):
        parts.append(html.escape(text[idx:match.start()]))
        if match.group(1) is not None:
            parts.append(f"<code>{html.escape(match.group(1))}</code>")
        elif match.group(2) is not None:
            label = html.escape(match.group(2))
            href = html.escape(match.group(3), quote=True)
            parts.append(f'<a href="{href}">{label}</a>')
        elif match.group(4) is not None:
            parts.append(f"<strong>{html.escape(match.group(4))}</strong>")
        else:
            parts.append(f"<em>{html.escape(match.group(5))}</em>")
        idx = match.end()
    parts.append(html.escape(text[idx:]))
    return "".join(parts)

"""
presentation/terminal.py
========================
Terminal Output Formatter & Presentation Polish Layer for Terminal News Assistant.

Responsibility (Presentation layer):
  Transforms raw retrieval results, aggregation context, and optional synthesis
  answers into a polished, readable, human-designed terminal presentation.

Design Principles:
  1. Clear visual hierarchy with clean section banners and consistent indentation.
  2. Safe cross-platform text wrapping without truncation of critical data.
  3. Honest status reporting (distinguishing SUCCESS + RESULTS, SUCCESS + 0 RESULTS, UNAVAILABLE).
  4. Pure functional formatting (no network, no LLMs, no retrieval imports, no data mutation).
  5. Deterministic and testable string generation.
"""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Constants & Layout Settings
# ---------------------------------------------------------------------------

DEFAULT_TERMINAL_WIDTH = 80
SECTION_DIVIDER_CHAR = "="
SUBSECTION_DIVIDER_CHAR = "-"


def _query_columns() -> int:
    """Query the system for the current terminal column width."""
    return shutil.get_terminal_size((DEFAULT_TERMINAL_WIDTH, 24)).columns


def get_terminal_width() -> int:
    """Get the current terminal width with safe fallback."""
    try:
        cols = _query_columns()
        return max(60, min(cols, 100))
    except Exception:
        return DEFAULT_TERMINAL_WIDTH


def _divider(char: str = SECTION_DIVIDER_CHAR, length: int | None = None) -> str:
    """Return a consistent horizontal divider line."""
    width = length or DEFAULT_TERMINAL_WIDTH
    return char * width


# ---------------------------------------------------------------------------
# Text Wrapping Helpers
# ---------------------------------------------------------------------------

def wrap_text(
    text: str,
    width: int | None = None,
    initial_indent: str = "",
    subsequent_indent: str = "",
) -> str:
    """
    Wrap plain text cleanly according to terminal width, preserving indentation.
    """
    if not text:
        return ""
    target_width = width or DEFAULT_TERMINAL_WIDTH
    wrapper = textwrap.TextWrapper(
        width=target_width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=True,
        break_on_hyphens=True,
    )
    return wrapper.fill(text)


def _check_mark() -> str:
    """Return an encoding-safe checkmark or [OK] status indicator."""
    check = "\u2713"
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        check.encode(encoding)
        return check
    except (UnicodeEncodeError, LookupError):
        return "[OK]"


# ---------------------------------------------------------------------------
# Header & Query Formatters
# ---------------------------------------------------------------------------

def format_banner(phase_label: str = "Phase 7") -> str:
    """Format the welcome status banner displayed at startup."""
    ok = _check_mark()
    div = _divider("=", 40)
    lines = [
        div,
        f"   TERMINAL NEWS ASSISTANT  ({phase_label})",
        div,
        "",
        "Retrieve live information from Google News RSS, Reddit, and DuckDuckGo,",
        "aggregate results, and synthesize a grounded AI summary.",
        "Type a search query and press Enter.",
        'Type "exit" or press Ctrl-C to quit.',
        "",
        f"  {ok} Python environment ready",
        f"  {ok} Google News RSS source ready",
        f"  {ok} Reddit source ready (requires credentials)",
        f"  {ok} DuckDuckGo web search source ready",
        f"  {ok} Context aggregation layer ready",
        f"  {ok} Optional LLM synthesis layer ready (requires OPENAI_API_KEY)",
        "",
        "Full terminal formatting polish will be added in later phases.",
        div,
    ]
    return "\n".join(lines)


def format_query_header(query: str) -> str:
    """Format the query header block."""
    clean_query = (query or "").strip()
    return f"Query: {clean_query}"


def format_source_summary(source_statuses: dict[str, Any]) -> str:
    """
    Format a compact status-at-a-glance summary for all retrieval sources.
    """
    lines = [
        "Sources Overview",
        _divider("-", 40),
    ]

    source_labels = [
        ("google_news", "Google News"),
        ("reddit", "Reddit"),
        ("duckduckgo", "Web Search"),
    ]

    for key, label in source_labels:
        status = source_statuses.get(key)
        if status is None:
            state_str = "not queried"
        elif not status.get("available"):
            err = status.get("error") or "unavailable"
            # Keep summary short
            short_err = err.split(":")[0] if ":" in err else err
            state_str = f"[UNAVAILABLE] ({short_err})"
        else:
            cnt = status.get("count", 0)
            state_str = f"{cnt} result{'s' if cnt != 1 else ''}"
        lines.append(f"  {label:<14} {state_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Google News Section Formatter
# ---------------------------------------------------------------------------

def format_google_news_results(query: str, results: list[dict] | None) -> str:
    """
    Format a list of Google News NewsItem dicts into a polished section.
    """
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "          GOOGLE NEWS RESULTS",
        div,
        f"Query: {query}",
        "",
    ]

    if not results:
        lines.append(f"No Google News results found for: {query}")
        lines.append(div)
        return "\n".join(lines)

    for i, item in enumerate(results, start=1):
        title = item.get("title", "No title")
        source = item.get("source", "Unknown")
        published = item.get("published", "Unknown date")
        link = item.get("link", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   Source:    {source}")
        lines.append(f"   Published: {published}")
        lines.append(f"   Link:      {link}")
        lines.append("")

    lines.append(div)
    return "\n".join(lines)


def format_google_news_error(message: str) -> str:
    """Format Google News source failure notice."""
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "          GOOGLE NEWS RESULTS",
        div,
        f"[UNAVAILABLE] {message}",
        div,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reddit Section Formatter
# ---------------------------------------------------------------------------

def format_reddit_results(query: str, results: list[dict] | None) -> str:
    """
    Format a list of Reddit RedditItem dicts into a polished section.
    """
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "            REDDIT RESULTS",
        div,
        f"Query: {query}",
        "",
    ]

    if not results:
        lines.append(f"No Reddit results found for: {query}")
        lines.append(div)
        return "\n".join(lines)

    for i, item in enumerate(results, start=1):
        title = item.get("title", "No title")
        subreddit = item.get("subreddit", "unknown")
        score = item.get("score", 0)
        comment_count = item.get("comment_count", 0)
        link = item.get("link", "")

        lines.append(f"{i}. {title}")
        lines.append(f"   Subreddit: r/{subreddit}")
        lines.append(f"   Score:     {score}")
        lines.append(f"   Comments:  {comment_count}")
        lines.append(f"   Link:      {link}")
        lines.append("")

    lines.append(div)
    return "\n".join(lines)


def format_reddit_error(message: str) -> str:
    """Format Reddit source failure notice."""
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "            REDDIT RESULTS",
        div,
        f"[UNAVAILABLE] {message}",
        div,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DuckDuckGo Section Formatter
# ---------------------------------------------------------------------------

def format_duckduckgo_results(query: str, results: list[dict] | None) -> str:
    """
    Format a list of DuckDuckGo WebItem dicts into a polished section.
    """
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "          WEB SEARCH RESULTS",
        div,
        f"Query: {query}",
        "",
    ]

    if not results:
        lines.append(f"No DuckDuckGo web results found for: {query}")
        lines.append(div)
        return "\n".join(lines)

    for i, item in enumerate(results, start=1):
        title = item.get("title", "No title")
        snippet = item.get("snippet", "")
        link = item.get("link", "")

        lines.append(f"{i}. {title}")
        if snippet:
            lines.append(f"   Snippet: {snippet}")
        lines.append(f"   Link:    {link}")
        lines.append("")

    lines.append(div)
    return "\n".join(lines)


def format_duckduckgo_error(message: str) -> str:
    """Format DuckDuckGo source failure notice."""
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "          WEB SEARCH RESULTS",
        div,
        f"[UNAVAILABLE] {message}",
        div,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Synthesis Section Formatter
# ---------------------------------------------------------------------------

def format_synthesis_summary(synthesis_result: dict, context: dict | None = None) -> str:
    """
    Format the AI summary response or informative notice.
    """
    div = _divider("=", 40)
    lines = [
        "",
        div,
        "               AI SUMMARY",
        div,
    ]

    if synthesis_result.get("available"):
        answer = synthesis_result.get("answer", "")
        lines.append(answer)

        # Show source provenance mapping if available
        source_ids = synthesis_result.get("source_ids", [])
        if source_ids and context and "items" in context:
            items = context["items"]
            citation_refs = []
            for sid in source_ids:
                # sid is like 'SOURCE_001'
                try:
                    num = int(sid.split("_")[1])
                    if 1 <= num <= len(items):
                        src_item = items[num - 1]
                        citation_refs.append(f"[{num}] {src_item.get('source', 'Source')}")
                except Exception:
                    pass
            if citation_refs:
                lines.append("")
                lines.append(f"Sources: {', '.join(citation_refs)}")
    else:
        error_msg = synthesis_result.get("error", "AI summary unavailable.")
        lines.append(f"[NOTE] {error_msg}")

    lines.append(div)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provenance Footer Formatter
# ---------------------------------------------------------------------------

def format_provenance_footer(context: dict) -> str:
    """
    Format a complete list of all retrieved sources with index numbers and links.
    """
    items = context.get("items", [])
    if not items:
        return ""

    lines = [
        "",
        "Sources & Provenance",
        _divider("-", 40),
    ]

    for idx, item in enumerate(items, start=1):
        stype = item.get("source_type", "")
        sname = item.get("source", "Source")
        title = item.get("title", "")
        link = item.get("link", "")
        lines.append(f"[{idx}] {title}")
        lines.append(f"    {sname} ({stype}) · {link}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full View Compositor
# ---------------------------------------------------------------------------

def render_full_output(
    query: str,
    context: dict,
    synthesis_result: dict | None = None,
) -> str:
    """
    Compose the entire query results into a single polished view.
    """
    parts = []
    source_statuses = context.get("source_statuses", {})

    # 1. Source Summary
    parts.append(format_source_summary(source_statuses))

    # 2. Synthesis (if available)
    if synthesis_result:
        parts.append(format_synthesis_summary(synthesis_result, context))

    return "\n".join(parts)

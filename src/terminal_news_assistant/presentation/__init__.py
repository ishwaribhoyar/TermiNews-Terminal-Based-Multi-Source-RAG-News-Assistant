"""
presentation/__init__.py
========================
Presentation & Terminal Output Formatting Layer for Terminal News Assistant.

Exports formatters for banners, source results, status summaries, AI synthesis,
and provenance citations.
"""

from terminal_news_assistant.presentation.terminal import (
    format_banner,
    format_duckduckgo_error,
    format_duckduckgo_results,
    format_google_news_error,
    format_google_news_results,
    format_provenance_footer,
    format_query_header,
    format_reddit_error,
    format_reddit_results,
    format_source_summary,
    format_synthesis_summary,
    render_full_output,
    wrap_text,
)

__all__ = [
    "format_banner",
    "format_duckduckgo_error",
    "format_duckduckgo_results",
    "format_google_news_error",
    "format_google_news_results",
    "format_provenance_footer",
    "format_query_header",
    "format_reddit_error",
    "format_reddit_results",
    "format_source_summary",
    "format_synthesis_summary",
    "render_full_output",
    "wrap_text",
]

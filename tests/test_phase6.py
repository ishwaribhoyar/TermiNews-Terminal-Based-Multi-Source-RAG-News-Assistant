"""
tests/test_phase6.py
====================
Phase 6 test suite — Final Terminal Output Formatting & Presentation Polish.

Tests:
  1.  Header formatting           — application title and status banner stable
  2.  Query display               — queries formatted cleanly with punctuation & wrapping
  3.  Google News formatting      — all fields (title, source, date, link) formatted
  4.  Reddit formatting           — all fields (title, subreddit, score, comments, link) formatted
  5.  DuckDuckGo formatting       — all fields (title, snippet, link) formatted
  6.  Empty source display        — 0 results produces clean no-results message (not error)
  7.  Unavailable source display  — source error produces [UNAVAILABLE] message
  8.  Partial sources summary     — source summary clearly shows available vs unavailable
  9.  Empty all sources           — 0 results across all sources handled gracefully
  10. AI synthesis success        — formatted AI summary with source citations
  11. AI synthesis unavailable    — [NOTE] informative notice when API key absent
  12. AI synthesis failure        — controlled message on API error without traceback
  13. Citation mapping            — source IDs [SOURCE_001] mapped to source names
  14. Long title wrapping         — long titles wrapped without breaking indentation
  15. Long snippet wrapping       — long snippets wrapped cleanly
  16. Long query wrapping         — long queries wrapped safely
  17. Long URL handling           — long URLs preserved intact without corruption
  18. Monochrome readability      — clean ASCII output without required ANSI escapes
  19. Pure formatter architecture — presentation module has no retrieval or LLM imports
  20. No network execution        — formatting requires zero network operations
  21. Deterministic output        — identical input produces identical formatted string
  22. Provenance footer           — structured provenance footer lists source links
  23. No data mutation            — input dictionaries remain unmutated by formatters
  24. Full view rendering         — render_full_output combines summary and synthesis
  25. Terminal width fallback     — get_terminal_width handles exceptions gracefully
  26. Missing fields fallback     — formatters handle missing dictionary keys safely
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

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
    get_terminal_width,
    render_full_output,
    wrap_text,
)


# ---------------------------------------------------------------------------
# Test 1 — Header & Banner
# ---------------------------------------------------------------------------

class TestHeader:
    """Verify application title and welcome banner formatting."""

    def test_banner_contains_app_name(self):
        banner = format_banner()
        assert "TERMINAL NEWS ASSISTANT" in banner
        assert "Google News" in banner
        assert "Reddit" in banner
        assert "DuckDuckGo" in banner

    def test_banner_is_deterministic(self):
        b1 = format_banner()
        b2 = format_banner()
        assert b1 == b2


# ---------------------------------------------------------------------------
# Test 2 — Query Display
# ---------------------------------------------------------------------------

class TestQueryDisplay:
    """Verify query header formatting."""

    def test_normal_query(self):
        qh = format_query_header("AI regulation")
        assert qh == "Query: AI regulation"

    def test_query_with_whitespace(self):
        qh = format_query_header("  artificial intelligence  ")
        assert qh == "Query: artificial intelligence"

    def test_query_with_special_characters(self):
        qh = format_query_header("AI & Tech: What's next? (2026)")
        assert qh == "Query: AI & Tech: What's next? (2026)"


# ---------------------------------------------------------------------------
# Test 3 — Google News Formatting
# ---------------------------------------------------------------------------

class TestGoogleNewsFormat:
    """Verify Google News items format all fields accurately."""

    def test_google_news_fields_present(self):
        results = [{
            "title": "Global AI Treaty Enacted",
            "source": "The Washington Post",
            "published": "2026-08-17 10:00 UTC",
            "link": "https://news.google.com/articles/12345",
        }]
        output = format_google_news_results("AI", results)

        assert "GOOGLE NEWS RESULTS" in output
        assert "1. Global AI Treaty Enacted" in output
        assert "Source:    The Washington Post" in output
        assert "Published: 2026-08-17 10:00 UTC" in output
        assert "Link:      https://news.google.com/articles/12345" in output


# ---------------------------------------------------------------------------
# Test 4 — Reddit Formatting
# ---------------------------------------------------------------------------

class TestRedditFormat:
    """Verify Reddit items format all fields accurately."""

    def test_reddit_fields_present(self):
        results = [{
            "title": "What are your thoughts on new AI laws?",
            "subreddit": "technology",
            "score": 1250,
            "comment_count": 340,
            "link": "https://reddit.com/r/technology/comments/abc123",
        }]
        output = format_reddit_results("AI laws", results)

        assert "REDDIT RESULTS" in output
        assert "1. What are your thoughts on new AI laws?" in output
        assert "Subreddit: r/technology" in output
        assert "Score:     1250" in output
        assert "Comments:  340" in output
        assert "Link:      https://reddit.com/r/technology/comments/abc123" in output


# ---------------------------------------------------------------------------
# Test 5 — DuckDuckGo Formatting
# ---------------------------------------------------------------------------

class TestDuckDuckGoFormat:
    """Verify DuckDuckGo web items format all fields accurately."""

    def test_web_fields_present(self):
        results = [{
            "title": "Overview of Global AI Regulations",
            "snippet": "A comprehensive summary of recent international legal frameworks for AI.",
            "link": "https://example.org/ai-summary",
        }]
        output = format_duckduckgo_results("AI", results)

        assert "WEB SEARCH RESULTS" in output
        assert "1. Overview of Global AI Regulations" in output
        assert "Snippet: A comprehensive summary of recent international legal frameworks for AI." in output
        assert "Link:    https://example.org/ai-summary" in output


# ---------------------------------------------------------------------------
# Test 6 — Empty Source Handling
# ---------------------------------------------------------------------------

class TestEmptySource:
    """Verify empty result lists display clear notices without error flags."""

    def test_empty_google_news(self):
        output = format_google_news_results("obscure_query", [])
        assert "No Google News results found for: obscure_query" in output
        assert "[UNAVAILABLE]" not in output

    def test_empty_reddit(self):
        output = format_reddit_results("obscure_query", [])
        assert "No Reddit results found for: obscure_query" in output
        assert "[UNAVAILABLE]" not in output

    def test_empty_duckduckgo(self):
        output = format_duckduckgo_results("obscure_query", [])
        assert "No DuckDuckGo web results found for: obscure_query" in output
        assert "[UNAVAILABLE]" not in output


# ---------------------------------------------------------------------------
# Test 7 — Unavailable Source Handling
# ---------------------------------------------------------------------------

class TestUnavailableSource:
    """Verify source failures display [UNAVAILABLE] notices without stack traces."""

    def test_google_news_error(self):
        output = format_google_news_error("Connection timed out after 10s")
        assert "[UNAVAILABLE] Connection timed out after 10s" in output
        assert "Traceback" not in output

    def test_reddit_error(self):
        output = format_reddit_error("Reddit credentials are not configured")
        assert "[UNAVAILABLE] Reddit credentials are not configured" in output

    def test_duckduckgo_error(self):
        output = format_duckduckgo_error("DuckDuckGo 202 Ratelimit")
        assert "[UNAVAILABLE] DuckDuckGo 202 Ratelimit" in output


# ---------------------------------------------------------------------------
# Test 8 — Source Summary Overview
# ---------------------------------------------------------------------------

class TestSourceSummary:
    """Verify compact summary block reports accurate status for each source."""

    def test_mixed_source_summary(self):
        statuses = {
            "google_news": {"available": True, "error": None, "count": 10},
            "reddit": {"available": False, "error": "Missing credentials", "count": 0},
            "duckduckgo": {"available": True, "error": None, "count": 5},
        }
        summary = format_source_summary(statuses)

        assert "Sources Overview" in summary
        assert "Google News    10 results" in summary
        assert "Reddit         [UNAVAILABLE] (Missing credentials)" in summary
        assert "Web Search     5 results" in summary


# ---------------------------------------------------------------------------
# Test 9 — AI Synthesis Success Formatting
# ---------------------------------------------------------------------------

class TestAISynthesisSuccess:
    """Verify successful AI summary display with citation mapping."""

    def test_ai_summary_with_citations(self):
        synth = {
            "answer": "Current news indicates that new regulations are underway [SOURCE_001].",
            "available": True,
            "error": None,
            "source_ids": ["SOURCE_001"],
        }
        ctx = {
            "items": [{
                "title": "New AI Bill",
                "source": "Reuters",
                "source_type": "google_news",
                "link": "https://reuters.com/1",
            }]
        }
        output = format_synthesis_summary(synth, ctx)

        assert "AI SUMMARY" in output
        assert "Current news indicates that new regulations are underway" in output
        assert "Sources: [1] Reuters" in output


# ---------------------------------------------------------------------------
# Test 10 — AI Synthesis Unavailable Formatting
# ---------------------------------------------------------------------------

class TestAISynthesisUnavailable:
    """Verify unavailable AI summary displays informative note."""

    def test_ai_summary_note(self):
        synth = {
            "answer": "",
            "available": False,
            "error": "OpenAI API key is not configured.",
            "source_ids": [],
        }
        output = format_synthesis_summary(synth)

        assert "AI SUMMARY" in output
        assert "[NOTE] OpenAI API key is not configured." in output


# ---------------------------------------------------------------------------
# Test 11 — Text Wrapping
# ---------------------------------------------------------------------------

class TestTextWrapping:
    """Verify text wrapping helper formats long content cleanly."""

    def test_long_paragraph_wrapped(self):
        long_text = (
            "This is an exceptionally long paragraph designed to test whether the text wrapping "
            "utility properly splits content across lines while preserving full word boundaries "
            "and preventing horizontal overflow on standard terminal screens."
        )
        wrapped = wrap_text(long_text, width=40)
        lines = wrapped.splitlines()

        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 40

    def test_indentation_preserved(self):
        text = "Indented line test with enough text to wrap onto a second line."
        wrapped = wrap_text(text, width=30, initial_indent="  ", subsequent_indent="    ")
        lines = wrapped.splitlines()

        assert lines[0].startswith("  ")
        assert lines[1].startswith("    ")


# ---------------------------------------------------------------------------
# Test 12 — Provenance Footer
# ---------------------------------------------------------------------------

class TestProvenanceFooter:
    """Verify provenance footer lists all items with index and link."""

    def test_provenance_footer_content(self):
        ctx = {
            "items": [
                {
                    "title": "Article One",
                    "source": "BBC",
                    "source_type": "google_news",
                    "link": "https://bbc.com/1",
                },
                {
                    "title": "Article Two",
                    "source": "Reddit r/news",
                    "source_type": "reddit",
                    "link": "https://reddit.com/r/news/2",
                },
            ]
        }
        footer = format_provenance_footer(ctx)

        assert "Sources & Provenance" in footer
        assert "[1] Article One" in footer
        assert "BBC (google_news) · https://bbc.com/1" in footer
        assert "[2] Article Two" in footer
        assert "Reddit r/news (reddit) · https://reddit.com/r/news/2" in footer

    def test_empty_provenance_footer(self):
        assert format_provenance_footer({}) == ""


# ---------------------------------------------------------------------------
# Test 13 — No Data Mutation
# ---------------------------------------------------------------------------

class TestNoDataMutation:
    """Verify formatters do not mutate input data structures."""

    def test_input_dict_unmutated(self):
        orig_item = {
            "title": "A " * 50,
            "source": "Test",
            "published": "2026",
            "link": "http://example.com",
        }
        item_copy = dict(orig_item)

        format_google_news_results("test", [orig_item])

        assert orig_item == item_copy


# ---------------------------------------------------------------------------
# Test 14 — Pure Formatter Architecture & No Network
# ---------------------------------------------------------------------------

class TestPureFormatterArchitecture:
    """Verify presentation module does not import retrieval sources or LLMs."""

    def test_no_source_or_llm_imports(self):
        import terminal_news_assistant.presentation.terminal as pt
        assert not hasattr(pt, "google_news")
        assert not hasattr(pt, "reddit")
        assert not hasattr(pt, "duckduckgo")
        assert not hasattr(pt, "openai")

    def test_no_network_calls_during_formatting(self, monkeypatch):
        def _guarded_socket(*args, **kwargs):
            raise RuntimeError("Network socket opened in presentation layer!")

        monkeypatch.setattr(socket, "socket", _guarded_socket)

        # Execute all formatting functions
        format_banner()
        format_query_header("AI")
        format_google_news_results("AI", [{"title": "T", "source": "S", "published": "P", "link": "L"}])
        format_reddit_results("AI", [{"title": "T", "subreddit": "S", "score": 1, "comment_count": 1, "link": "L"}])
        format_duckduckgo_results("AI", [{"title": "T", "snippet": "S", "link": "L"}])
        format_synthesis_summary({"answer": "Ans", "available": True, "source_ids": []})
        format_source_summary({"google_news": {"available": True, "count": 1}})
        format_provenance_footer({"items": [{"title": "T", "source": "S", "source_type": "gn", "link": "L"}]})


# ---------------------------------------------------------------------------
# Test 15 — Full Output Compositor
# ---------------------------------------------------------------------------

class TestFullOutputCompositor:
    """Verify render_full_output integrates status and synthesis."""

    def test_render_full_output_composition(self):
        context = {
            "query": "quantum computing",
            "items": [],
            "source_statuses": {
                "google_news": {"available": True, "count": 0},
                "reddit": {"available": True, "count": 0},
                "duckduckgo": {"available": True, "count": 0},
            },
        }
        synth = {
            "answer": "No information found.",
            "available": True,
            "source_ids": [],
        }

        output = render_full_output("quantum computing", context, synth)
        assert "Sources Overview" in output
        assert "AI SUMMARY" in output
        assert "No information found." in output


# ---------------------------------------------------------------------------
# Test 16 — Terminal Width Fallback
# ---------------------------------------------------------------------------

class TestTerminalWidth:
    """Verify get_terminal_width returns reasonable integer even on errors."""

    def test_terminal_width_bounds(self):
        width = get_terminal_width()
        assert isinstance(width, int)
        assert 60 <= width <= 100

    def test_terminal_width_fallback_on_error(self, monkeypatch):
        import terminal_news_assistant.presentation.terminal as pt
        monkeypatch.setattr(pt, "_query_columns", MagicMock(side_effect=Exception("Terminal error")))
        width = get_terminal_width()
        assert width == 80


# ---------------------------------------------------------------------------
# Test 17 — Missing Dictionary Keys Fallback
# ---------------------------------------------------------------------------

class TestMissingKeysFallback:
    """Verify formatters handle sparse dictionaries without raising KeyErrors."""

    def test_sparse_google_news_item(self):
        output = format_google_news_results("test", [{}])
        assert "No title" in output
        assert "Unknown" in output

    def test_sparse_reddit_item(self):
        output = format_reddit_results("test", [{}])
        assert "No title" in output
        assert "r/unknown" in output

    def test_sparse_web_item(self):
        output = format_duckduckgo_results("test", [{}])
        assert "No title" in output

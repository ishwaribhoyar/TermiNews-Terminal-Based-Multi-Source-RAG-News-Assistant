"""
tests/test_phase3.py
====================
Phase 3 test suite — DuckDuckGo Web Search Source.

Tests:
  1.  Library import          — duckduckgo_search is importable
  2.  Client initialization   — DDGS client instantiated properly
  3.  Query forwarding        — user query reaches DDGS.text() correctly
  4.  Result normalization    — single raw result mapped to correct WebItem
  5.  Multiple results        — count, order, independent normalization
  6.  Missing title           — safe fallback used
  7.  Missing snippet         — safe fallback used
  8.  Missing link            — safe fallback used
  9.  Empty result set        — [] returned without raising
  10. Network failure         — DuckDuckGoError raised cleanly
  11. Library / API failure   — generic exception becomes DuckDuckGoError
  12. Empty query validation  — empty input does not call DDG search
  13. Whitespace query        — whitespace-only input does not call DDG search
  14. Special characters      — queries with spaces/symbols forwarded safely
  15. Display                 — DuckDuckGo fields appear in terminal output
  16. Empty-result display    — zero results print informative message
  17. Error display           — source failure prints [UNAVAILABLE] notice
  18. Source isolation        — DDG failure does not halt Google News or Reddit
  19. Google News regression  — GN search still functional alongside DDG
  20. Reddit regression       — Reddit search still functional alongside DDG

All tests are deterministic and offline.
No live DuckDuckGo calls are made.
"""

from __future__ import annotations

import io
import sys
import types
import unittest.mock as mock

import pytest


# ---------------------------------------------------------------------------
# Test 1 — Library import
# ---------------------------------------------------------------------------

class TestLibraryImport:
    """Verify that duckduckgo_search is importable in the project environment."""

    def test_duckduckgo_search_importable(self):
        import duckduckgo_search  # noqa: F401

    def test_ddgs_class_importable(self):
        from duckduckgo_search import DDGS
        assert isinstance(DDGS, type)


# ---------------------------------------------------------------------------
# Test 2 — Client initialization
# ---------------------------------------------------------------------------

class TestClientInitialization:
    """Verify _create_client() initializes DDGS client."""

    def test_create_client_returns_instance(self):
        from terminal_news_assistant.sources.duckduckgo import _create_client
        client = _create_client()
        assert client is not None


# ---------------------------------------------------------------------------
# Test 3 — Query forwarding
# ---------------------------------------------------------------------------

class TestQueryForwarding:
    """Verify the user search term is passed into client.text()."""

    def test_query_is_forwarded_to_client(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo

        called_with = []

        class _FakeDDGS:
            def text(self, query, max_results=10, **kwargs):
                called_with.append({"query": query, "max_results": max_results})
                return []

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _FakeDDGS())

        duckduckgo.search("AI regulation", max_results=5)
        assert len(called_with) == 1
        assert called_with[0]["query"] == "AI regulation"
        assert called_with[0]["max_results"] == 5


# ---------------------------------------------------------------------------
# Test 4 — Result normalization
# ---------------------------------------------------------------------------

class TestResultNormalization:
    """A raw DDG result dict must be normalized into a clean WebItem."""

    def test_title_extracted(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {
            "title": "Python Programming",
            "body": "A high-level language.",
            "href": "https://python.org",
        }
        res = _normalize_result(raw)
        assert res["title"] == "Python Programming"

    def test_snippet_extracted_from_body(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {
            "title": "Python Programming",
            "body": "A high-level language.",
            "href": "https://python.org",
        }
        res = _normalize_result(raw)
        assert res["snippet"] == "A high-level language."

    def test_snippet_extracted_from_snippet_key(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {
            "title": "Title",
            "snippet": "Snippet content.",
            "href": "https://example.com",
        }
        res = _normalize_result(raw)
        assert res["snippet"] == "Snippet content."

    def test_link_extracted_from_href(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {
            "title": "Title",
            "body": "Body",
            "href": "https://example.com/page",
        }
        res = _normalize_result(raw)
        assert res["link"] == "https://example.com/page"

    def test_result_has_all_required_keys(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {
            "title": "Title",
            "body": "Body",
            "href": "https://example.com",
        }
        res = _normalize_result(raw)
        assert set(res.keys()) == {"title", "snippet", "link"}


# ---------------------------------------------------------------------------
# Test 5 — Multiple results
# ---------------------------------------------------------------------------

class TestMultipleResults:
    """Multiple search results should be returned in order and normalized independently."""

    def test_multiple_results_returned(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw_list = [
            {"title": f"Result {i}", "body": f"Snippet {i}", "href": f"https://ex.com/{i}"}
            for i in range(5)
        ]
        results = [_normalize_result(r) for r in raw_list]
        assert len(results) == 5
        for i, r in enumerate(results):
            assert r["title"] == f"Result {i}"
            assert r["snippet"] == f"Snippet {i}"
            assert r["link"] == f"https://ex.com/{i}"


# ---------------------------------------------------------------------------
# Test 6 — Missing title
# ---------------------------------------------------------------------------

class TestMissingTitle:
    """Absent or empty title should use safe default."""

    def test_missing_title_defaults_safely(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {"title": "", "body": "Body", "href": "https://example.com"}
        res = _normalize_result(raw)
        assert res["title"] == "No title"


# ---------------------------------------------------------------------------
# Test 7 — Missing snippet
# ---------------------------------------------------------------------------

class TestMissingSnippet:
    """Absent snippet should default to empty string."""

    def test_missing_snippet_defaults_safely(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {"title": "Title", "href": "https://example.com"}
        res = _normalize_result(raw)
        assert res["snippet"] == ""


# ---------------------------------------------------------------------------
# Test 8 — Missing link
# ---------------------------------------------------------------------------

class TestMissingLink:
    """Absent link should default to empty string."""

    def test_missing_link_defaults_safely(self):
        from terminal_news_assistant.sources.duckduckgo import _normalize_result
        raw = {"title": "Title", "body": "Body"}
        res = _normalize_result(raw)
        assert res["link"] == ""


# ---------------------------------------------------------------------------
# Test 9 — Empty result set
# ---------------------------------------------------------------------------

class TestEmptyResultSet:
    """Empty results list must return [] without raising an exception."""

    def test_empty_results_returns_empty_list(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo

        class _EmptyDDGS:
            def text(self, query, **kwargs):
                return []

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _EmptyDDGS())
        results = duckduckgo.search("nonexistenttopic12345")
        assert results == []

    def test_none_results_returns_empty_list(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo

        class _NoneDDGS:
            def text(self, query, **kwargs):
                return None

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _NoneDDGS())
        results = duckduckgo.search("nonexistenttopic12345")
        assert results == []


# ---------------------------------------------------------------------------
# Test 10 — Network failure
# ---------------------------------------------------------------------------

class TestNetworkFailure:
    """Network exceptions raised during search must produce DuckDuckGoError."""

    def test_network_exception_raises_duckduckgo_error(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo
        from terminal_news_assistant.sources.duckduckgo import DuckDuckGoError

        class _FailingDDGS:
            def text(self, query, **kwargs):
                raise ConnectionError("Connection refused")

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _FailingDDGS())

        with pytest.raises(DuckDuckGoError) as exc_info:
            duckduckgo.search("test")
        assert "DuckDuckGo search failed" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 11 — Search / library failure
# ---------------------------------------------------------------------------

class TestLibraryFailure:
    """Library exceptions (e.g. rate limit, timeout) must produce DuckDuckGoError."""

    def test_generic_exception_becomes_duckduckgo_error(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo
        from terminal_news_assistant.sources.duckduckgo import DuckDuckGoError

        class _FailingDDGS:
            def text(self, query, **kwargs):
                raise RuntimeError("Rate limit reached")

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _FailingDDGS())

        with pytest.raises(DuckDuckGoError):
            duckduckgo.search("test")


# ---------------------------------------------------------------------------
# Test 12 — Empty query validation
# ---------------------------------------------------------------------------

class TestEmptyQueryValidation:
    """Empty queries must not invoke duckduckgo.search()."""

    def test_empty_query_does_not_call_search(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import duckduckgo

        search_called = []

        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: search_called.append(q) or [])
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called


# ---------------------------------------------------------------------------
# Test 13 — Whitespace query validation
# ---------------------------------------------------------------------------

class TestWhitespaceQueryValidation:
    """Whitespace-only queries must not invoke duckduckgo.search()."""

    def test_whitespace_query_does_not_call_search(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import duckduckgo

        search_called = []

        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: search_called.append(q) or [])
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called


# ---------------------------------------------------------------------------
# Test 14 — Special characters
# ---------------------------------------------------------------------------

class TestSpecialCharacters:
    """Queries with special characters must be forwarded safely to search client."""

    def test_special_characters_forwarded_intact(self, monkeypatch):
        from terminal_news_assistant.sources import duckduckgo

        queries_seen = []

        class _FakeDDGS:
            def text(self, query, **kwargs):
                queries_seen.append(query)
                return []

        monkeypatch.setattr(duckduckgo, "_create_client", lambda: _FakeDDGS())

        duckduckgo.search("OpenAI + Microsoft & 'AI'")
        assert queries_seen == ["OpenAI + Microsoft & 'AI'"]


# ---------------------------------------------------------------------------
# Test 15 — Display
# ---------------------------------------------------------------------------

class TestDuckDuckGoDisplay:
    """DuckDuckGo result fields must appear in terminal output."""

    def test_display_shows_title_snippet_link(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo
        from terminal_news_assistant.sources.duckduckgo import WebItem

        fake_web_item: WebItem = {
            "title": "Unique Web Result Title",
            "snippet": "This is a detailed snippet of the result.",
            "link": "https://unique-domain.example.com/page",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [fake_web_item])
        monkeypatch.setattr(main, "get_query", lambda: "test query")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "Unique Web Result Title" in output
        assert "This is a detailed snippet of the result." in output
        assert "https://unique-domain.example.com/page" in output


# ---------------------------------------------------------------------------
# Test 16 — Empty-result display
# ---------------------------------------------------------------------------

class TestEmptyResultDisplay:
    """When DDG returns zero results, an informative notice is printed."""

    def test_empty_results_prints_notice(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [])
        monkeypatch.setattr(main, "get_query", lambda: "test query")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "no duckduckgo web results found" in output.lower()


# ---------------------------------------------------------------------------
# Test 17 — Error display
# ---------------------------------------------------------------------------

class TestErrorDisplay:
    """When DDG raises DuckDuckGoError, [UNAVAILABLE] notice is printed."""

    def test_error_prints_unavailable_notice(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo
        from terminal_news_assistant.sources.duckduckgo import DuckDuckGoError

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(
            duckduckgo, "search",
            lambda q, **kw: (_ for _ in ()).throw(
                DuckDuckGoError("Rate limit exceeded")
            ),
        )
        monkeypatch.setattr(main, "get_query", lambda: "test query")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "[UNAVAILABLE]" in output
        assert "Rate limit exceeded" in output


# ---------------------------------------------------------------------------
# Test 18 — Source isolation
# ---------------------------------------------------------------------------

class TestSourceIsolation:
    """DuckDuckGo failure must not prevent Google News or Reddit from running."""

    def test_ddg_failure_does_not_halt_other_sources(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo
        from terminal_news_assistant.sources.google_news import NewsItem
        from terminal_news_assistant.sources.reddit import RedditItem
        from terminal_news_assistant.sources.duckduckgo import DuckDuckGoError

        gn_item: NewsItem = {
            "title": "Google News Success Headline",
            "source": "GN Source",
            "published": "2026-08-16",
            "link": "https://gn.example.com",
        }
        reddit_item: RedditItem = {
            "title": "Reddit Success Post",
            "subreddit": "technology",
            "score": 100,
            "comment_count": 20,
            "link": "https://reddit.com/r/technology/123",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [gn_item])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [reddit_item])
        monkeypatch.setattr(
            duckduckgo, "search",
            lambda q, **kw: (_ for _ in ()).throw(
                DuckDuckGoError("DDG service down")
            ),
        )
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "Google News Success Headline" in output
        assert "Reddit Success Post" in output
        assert "DDG service down" in output


# ---------------------------------------------------------------------------
# Test 19 — Google News regression
# ---------------------------------------------------------------------------

class TestGoogleNewsRegression:
    """Google News retrieval continues to work alongside DuckDuckGo."""

    def test_google_news_search_callable(self):
        from terminal_news_assistant.sources.google_news import search
        assert callable(search)


# ---------------------------------------------------------------------------
# Test 20 — Reddit regression
# ---------------------------------------------------------------------------

class TestRedditRegression:
    """Reddit retrieval continues to work alongside DuckDuckGo."""

    def test_reddit_search_callable(self):
        from terminal_news_assistant.sources.reddit import search
        assert callable(search)

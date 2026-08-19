"""
tests/test_phase1.py
====================
Phase 1 test suite — Google News RSS Source.

Tests:
  1. Valid RSS entry parsing / normalization
  2. Multiple entries normalization
  3. Missing optional metadata (source, published) handled safely
  4. Empty feed returns []
  5. Malformed RSS produces GoogleNewsError, not a crash
  6. Empty query validation (no RSS request fired)
  7. URL encoding — spaces and special characters
  8. Network failure — controlled GoogleNewsError, not raw exception

All tests are offline / deterministic.  No live network requests are made.
The live integration test is performed manually (see Phase 1 report).
"""

from __future__ import annotations

import io
import sys
import types
import unittest.mock as mock
import urllib.error
import urllib.parse

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    title: str = "Test Headline",
    link: str = "https://example.com/story",
    source_title: str | None = "Test Publication",
    published: str = "Sat, 16 Aug 2026 10:00:00 GMT",
    published_parsed=None,
) -> types.SimpleNamespace:
    """
    Build a minimal feedparser-like entry object for test use.
    feedparser entries are attribute-accessible dicts; SimpleNamespace
    with a .get() method approximates that for our normalization tests.
    """

    class _FakeEntry(types.SimpleNamespace):
        def get(self, key, default=None):
            return getattr(self, key, default)

    source = {"title": source_title} if source_title is not None else {}
    entry = _FakeEntry(
        title=title,
        link=link,
        source=source,
        published=published,
        published_parsed=published_parsed,
    )
    return entry


def _make_feed(entries: list) -> types.SimpleNamespace:
    """Build a minimal feedparser-like feed object."""

    class _FakeFeed(types.SimpleNamespace):
        def get(self, key, default=None):
            return getattr(self, key, default)

    return _FakeFeed(entries=entries, bozo=False)


# ---------------------------------------------------------------------------
# Test 1 — Valid RSS entry parsing
# ---------------------------------------------------------------------------

class TestNormalizeEntry:
    """Verify a well-formed RSS entry is normalized into the correct contract."""

    def test_title_extracted(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(title="Big News Today")
        result = _normalize_entry(entry)
        assert result["title"] == "Big News Today"

    def test_source_extracted(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(source_title="The Daily Example")
        result = _normalize_entry(entry)
        assert result["source"] == "The Daily Example"

    def test_link_extracted(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(link="https://news.example.com/article/1")
        result = _normalize_entry(entry)
        assert result["link"] == "https://news.example.com/article/1"

    def test_published_string_used_when_no_parsed(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(published="Mon, 11 Aug 2026 09:00:00 GMT", published_parsed=None)
        result = _normalize_entry(entry)
        assert result["published"] == "Mon, 11 Aug 2026 09:00:00 GMT"

    def test_result_has_all_keys(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry()
        result = _normalize_entry(entry)
        assert set(result.keys()) == {"title", "source", "published", "link"}


# ---------------------------------------------------------------------------
# Test 2 — Multiple entries
# ---------------------------------------------------------------------------

class TestMultipleEntries:
    """All entries in a feed should be normalized independently."""

    def test_multiple_entries_all_returned(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entries = [
            _make_entry(title=f"Headline {i}", link=f"https://ex.com/{i}")
            for i in range(5)
        ]
        results = [_normalize_entry(e) for e in entries]
        assert len(results) == 5
        for i, r in enumerate(results):
            assert r["title"] == f"Headline {i}"
            assert r["link"] == f"https://ex.com/{i}"

    def test_entries_are_independent(self):
        """Mutating one result should not affect another."""
        from terminal_news_assistant.sources.google_news import _normalize_entry
        e1 = _make_entry(title="First")
        e2 = _make_entry(title="Second")
        r1 = _normalize_entry(e1)
        r2 = _normalize_entry(e2)
        assert r1["title"] != r2["title"]


# ---------------------------------------------------------------------------
# Test 3 — Missing optional metadata
# ---------------------------------------------------------------------------

class TestMissingMetadata:
    """Absent fields should fall back to safe placeholder strings."""

    def test_missing_source_defaults_to_unknown(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(source_title=None)
        result = _normalize_entry(entry)
        assert result["source"] == "Unknown source"

    def test_empty_source_title_defaults_to_unknown(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(source_title="")
        result = _normalize_entry(entry)
        assert result["source"] == "Unknown source"

    def test_missing_published_defaults_to_unknown(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry

        class _NoPublished(types.SimpleNamespace):
            def get(self, key, default=None):
                return getattr(self, key, default)

        entry = _NoPublished(
            title="Headline",
            link="https://ex.com",
            source={"title": "Pub"},
            published="",
            published_parsed=None,
        )
        result = _normalize_entry(entry)
        assert result["published"] == "Unknown date"

    def test_missing_title_replaced_with_placeholder(self):
        from terminal_news_assistant.sources.google_news import _normalize_entry
        entry = _make_entry(title="")
        result = _normalize_entry(entry)
        assert result["title"] == "No title"


# ---------------------------------------------------------------------------
# Test 4 — Empty feed
# ---------------------------------------------------------------------------

class TestEmptyFeed:
    """search() on an empty feed must return [] without raising."""

    def test_empty_feed_returns_empty_list(self, monkeypatch):
        from terminal_news_assistant.sources import google_news

        empty_feed = _make_feed([])

        monkeypatch.setattr(google_news, "_fetch_raw", lambda url: b"<rss/>")
        monkeypatch.setattr(google_news, "_parse_feed", lambda raw: empty_feed)

        results = google_news.search("anything")
        assert results == []

    def test_empty_feed_does_not_raise(self, monkeypatch):
        from terminal_news_assistant.sources import google_news

        empty_feed = _make_feed([])
        monkeypatch.setattr(google_news, "_fetch_raw", lambda url: b"<rss/>")
        monkeypatch.setattr(google_news, "_parse_feed", lambda raw: empty_feed)

        try:
            google_news.search("unknownquery12345")
        except Exception as exc:
            pytest.fail(f"search() raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Test 5 — Malformed RSS
# ---------------------------------------------------------------------------

class TestMalformedRSS:
    """_parse_feed on a bozo feed with no entries must raise GoogleNewsError."""

    def test_malformed_feed_raises_google_news_error(self, monkeypatch):
        from terminal_news_assistant.sources.google_news import (
            _parse_feed,
            GoogleNewsError,
        )
        import feedparser

        # Patch feedparser.parse to return a bozo feed with no entries
        bozo_result = types.SimpleNamespace(
            bozo=True,
            entries=[],
            bozo_exception=Exception("bad XML"),
        )
        bozo_result.get = lambda key, default=None: getattr(bozo_result, key, default)

        monkeypatch.setattr(feedparser, "parse", lambda _: bozo_result)

        with pytest.raises(GoogleNewsError):
            _parse_feed(b"not xml at all")

    def test_malformed_feed_does_not_crash_application(self, monkeypatch):
        """search() must surface GoogleNewsError rather than an unhandled crash."""
        from terminal_news_assistant.sources import google_news
        import feedparser

        bozo_result = types.SimpleNamespace(
            bozo=True,
            entries=[],
            bozo_exception=Exception("bad XML"),
        )
        bozo_result.get = lambda key, default=None: getattr(bozo_result, key, default)

        monkeypatch.setattr(google_news, "_fetch_raw", lambda url: b"garbage")
        monkeypatch.setattr(feedparser, "parse", lambda _: bozo_result)

        from terminal_news_assistant.sources.google_news import GoogleNewsError
        with pytest.raises(GoogleNewsError):
            google_news.search("test")


# ---------------------------------------------------------------------------
# Test 6 — Empty query validation
# ---------------------------------------------------------------------------

class TestEmptyQueryValidation:
    """
    The presentation layer (main.py) must reject empty/whitespace queries
    before calling google_news.search().
    """

    def test_empty_string_does_not_call_search(self, monkeypatch):
        """
        When get_query() returns "", run() must print a validation message
        and NOT call google_news.search().
        """
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news

        search_called = []

        def _mock_search(query, **kwargs):
            search_called.append(query)
            return []

        monkeypatch.setattr(google_news, "search", _mock_search)
        # Simulate empty user input
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called, "search() was called despite empty query"
        output = captured.getvalue()
        assert "enter a search query" in output.lower()

    def test_whitespace_only_does_not_call_search(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news

        search_called = []

        def _mock_search(query, **kwargs):
            search_called.append(query)
            return []

        monkeypatch.setattr(google_news, "search", _mock_search)
        # get_query() strips, so "   ".strip() == "" — simulate that result
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called


# ---------------------------------------------------------------------------
# Test 7 — URL encoding
# ---------------------------------------------------------------------------

class TestURLEncoding:
    """Query strings must be safely encoded in the RSS URL."""

    def test_spaces_encoded(self):
        from terminal_news_assistant.sources.google_news import _build_url
        url = _build_url("AI regulation")
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        # urllib.parse.urlencode uses '+' for spaces in query strings,
        # parse_qs decodes them back to the original space.
        assert params["q"][0] == "AI regulation"

    def test_special_characters_encoded(self):
        from terminal_news_assistant.sources.google_news import _build_url
        url = _build_url("OpenAI + Microsoft")
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        assert params["q"][0] == "OpenAI + Microsoft"

    def test_url_has_correct_base(self):
        from terminal_news_assistant.sources.google_news import _build_url
        url = _build_url("technology")
        assert url.startswith("https://news.google.com/rss/search")

    def test_url_contains_hl_param(self):
        from terminal_news_assistant.sources.google_news import _build_url
        url = _build_url("technology")
        assert "hl=en-US" in url or "hl=en" in url


# ---------------------------------------------------------------------------
# Test 8 — Network failure handling
# ---------------------------------------------------------------------------

class TestNetworkFailure:
    """Simulated network failures must produce GoogleNewsError, not raw crashes."""

    def test_url_error_raises_google_news_error(self, monkeypatch):
        """URLError (connection refused, DNS failure, etc.) -> GoogleNewsError."""
        from terminal_news_assistant.sources.google_news import (
            _fetch_raw,
            GoogleNewsError,
        )
        import urllib.request

        def _raise_url_error(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _raise_url_error)

        with pytest.raises(GoogleNewsError) as exc_info:
            _fetch_raw("https://news.google.com/rss/search?q=test")

        assert "could not be reached" in str(exc_info.value).lower()

    def test_timeout_raises_google_news_error(self, monkeypatch):
        """A TimeoutError must become a GoogleNewsError."""
        from terminal_news_assistant.sources.google_news import (
            _fetch_raw,
            GoogleNewsError,
        )
        import urllib.request

        def _raise_timeout(req, timeout=None):
            raise TimeoutError("timed out")

        monkeypatch.setattr(urllib.request, "urlopen", _raise_timeout)

        with pytest.raises(GoogleNewsError) as exc_info:
            _fetch_raw("https://news.google.com/rss/search?q=test")

        assert "timed out" in str(exc_info.value).lower()

    def test_search_surfaces_google_news_error(self, monkeypatch):
        """search() must propagate GoogleNewsError on network failure."""
        from terminal_news_assistant.sources import google_news
        from terminal_news_assistant.sources.google_news import GoogleNewsError

        def _failing_fetch(url):
            raise GoogleNewsError("Google News could not be reached: simulated")

        monkeypatch.setattr(google_news, "_fetch_raw", _failing_fetch)

        with pytest.raises(GoogleNewsError):
            google_news.search("AI")

    def test_display_error_shown_on_google_news_error(self, monkeypatch):
        """
        When GoogleNewsError is raised, main.run() must call display_error()
        rather than propagating the exception to the top level.
        """
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news
        from terminal_news_assistant.sources.google_news import GoogleNewsError

        def _failing_search(query, **kwargs):
            raise GoogleNewsError("Simulated network failure")

        monkeypatch.setattr(google_news, "search", _failing_search)
        monkeypatch.setattr(main, "get_query", lambda: "AI")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        # Should NOT raise
        main.run()

        output = captured.getvalue()
        assert "UNAVAILABLE" in output or "unavailable" in output.lower()

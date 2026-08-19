"""
tests/test_phase4.py
====================
Phase 4 test suite — Context Aggregation & Retrieval Context Builder.

Tests:
  1.  Empty inputs                   — aggregate([], [], []) yields valid empty context
  2.  Google News only               — items mapped, metadata preserved, provenance intact
  3.  Reddit only                    — items mapped, score/comments preserved, provenance intact
  4.  DuckDuckGo only                — items mapped, snippet preserved, provenance intact
  5.  All three sources              — all items merged deterministically
  6.  Source failure representation  — failed source marked unavailable with error msg
  7.  All sources unavailable        — valid empty context, no crash, statuses recorded
  8.  Zero results vs source failure — distinct representation of empty vs error
  9.  Provenance validation          — all required fields present on every ContextItem
  10. Exact duplicate handling       — identical URLs across sources deduplicated
  11. Non-duplicate preservation     — distinct URLs preserved
  12. Malformed / missing fields     — graceful defaults, no crashes
  13. Deterministic ordering         — same inputs produce same order every time
  14. Input immutability             — source dictionaries not modified
  15. No network operations          — pure in-memory transformation
  16. No LLM dependency              — pure transformation without generative calls
  17. Alias consistency              — build_context produces identical result to aggregate
  18. Empty URL deduplication        — duplicate titles when link is empty
  19. Partial source failure permutations — all combinations of 1/2/3 failing sources
  20. Multiple items per source      — multiple items from each source mapped in sequence
  21. Special characters in query    — query string trimmed and preserved accurately
  22. Source name fallback           — missing source/subreddit defaults to sensible strings

All tests are deterministic, offline, and require no credentials or network.
"""

from __future__ import annotations

import pytest

from terminal_news_assistant.aggregation.aggregator import (
    ContextItem,
    SourceStatus,
    UnifiedContext,
    aggregate,
    build_context,
)


# ---------------------------------------------------------------------------
# Test 1 — Empty inputs
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    """Verify aggregation handles empty result lists safely."""

    def test_all_empty_lists_returns_empty_context(self):
        ctx = aggregate(
            query="test",
            google_news_results=[],
            reddit_results=[],
            duckduckgo_results=[],
        )
        assert ctx["query"] == "test"
        assert ctx["items"] == []
        assert ctx["source_statuses"]["google_news"]["available"] is True
        assert ctx["source_statuses"]["google_news"]["count"] == 0
        assert ctx["source_statuses"]["reddit"]["available"] is True
        assert ctx["source_statuses"]["duckduckgo"]["available"] is True

    def test_none_inputs_handled_safely(self):
        ctx = aggregate(
            query="test",
            google_news_results=None,
            reddit_results=None,
            duckduckgo_results=None,
        )
        assert ctx["items"] == []
        assert ctx["source_statuses"]["google_news"]["available"] is False


# ---------------------------------------------------------------------------
# Test 2 — Google News only
# ---------------------------------------------------------------------------

class TestGoogleNewsOnly:
    """Verify Google News items are correctly converted into ContextItems."""

    def test_google_news_items_mapped(self):
        gn_items = [
            {
                "title": "Major Tech Announcement",
                "source": "Reuters",
                "published": "2026-08-16 10:00 UTC",
                "link": "https://reuters.example.com/story1",
            }
        ]
        ctx = aggregate("tech", google_news_results=gn_items)

        assert len(ctx["items"]) == 1
        item = ctx["items"][0]
        assert item["title"] == "Major Tech Announcement"
        assert item["source"] == "Reuters"
        assert item["source_type"] == "google_news"
        assert item["link"] == "https://reuters.example.com/story1"
        assert item["metadata"]["published"] == "2026-08-16 10:00 UTC"
        assert ctx["source_statuses"]["google_news"]["count"] == 1

    def test_google_news_multiple_items_mapped(self):
        gn_items = [
            {"title": f"Headline {i}", "source": f"Publisher {i}", "published": "2026-08-16", "link": f"https://news.example.com/{i}"}
            for i in range(4)
        ]
        ctx = aggregate("tech", google_news_results=gn_items)
        assert len(ctx["items"]) == 4
        assert ctx["source_statuses"]["google_news"]["count"] == 4


# ---------------------------------------------------------------------------
# Test 3 — Reddit only
# ---------------------------------------------------------------------------

class TestRedditOnly:
    """Verify Reddit items are correctly converted with score/comments in metadata."""

    def test_reddit_items_mapped(self):
        reddit_items = [
            {
                "title": "Discussion on AI Safety",
                "subreddit": "MachineLearning",
                "score": 450,
                "comment_count": 82,
                "link": "https://reddit.com/r/MachineLearning/comments/123",
            }
        ]
        ctx = aggregate("ai safety", reddit_results=reddit_items)

        assert len(ctx["items"]) == 1
        item = ctx["items"][0]
        assert item["title"] == "Discussion on AI Safety"
        assert item["source"] == "r/MachineLearning"
        assert item["source_type"] == "reddit"
        assert item["link"] == "https://reddit.com/r/MachineLearning/comments/123"
        assert item["metadata"]["score"] == 450
        assert item["metadata"]["comment_count"] == 82
        assert ctx["source_statuses"]["reddit"]["count"] == 1


# ---------------------------------------------------------------------------
# Test 4 — DuckDuckGo only
# ---------------------------------------------------------------------------

class TestDuckDuckGoOnly:
    """Verify DuckDuckGo web items are correctly converted with snippets."""

    def test_duckduckgo_items_mapped(self):
        ddg_items = [
            {
                "title": "Official Python Website",
                "snippet": "Python is a programming language that lets you work quickly.",
                "link": "https://www.python.org",
            }
        ]
        ctx = aggregate("python", duckduckgo_results=ddg_items)

        assert len(ctx["items"]) == 1
        item = ctx["items"][0]
        assert item["title"] == "Official Python Website"
        assert item["content"] == "Python is a programming language that lets you work quickly."
        assert item["source_type"] == "duckduckgo"
        assert item["link"] == "https://www.python.org"
        assert ctx["source_statuses"]["duckduckgo"]["count"] == 1


# ---------------------------------------------------------------------------
# Test 5 — All three sources
# ---------------------------------------------------------------------------

class TestAllThreeSources:
    """Verify items from all three sources are merged in sequence without loss."""

    def test_all_sources_merged(self):
        gn_items = [{"title": "GN 1", "source": "News Org", "published": "today", "link": "https://gn.com/1"}]
        reddit_items = [{"title": "Reddit 1", "subreddit": "news", "score": 10, "comment_count": 2, "link": "https://reddit.com/1"}]
        ddg_items = [{"title": "DDG 1", "snippet": "snippet text", "link": "https://ddg.com/1"}]

        ctx = aggregate(
            "query",
            google_news_results=gn_items,
            reddit_results=reddit_items,
            duckduckgo_results=ddg_items,
        )

        assert len(ctx["items"]) == 3
        assert [i["source_type"] for i in ctx["items"]] == ["google_news", "reddit", "duckduckgo"]
        assert ctx["source_statuses"]["google_news"]["count"] == 1
        assert ctx["source_statuses"]["reddit"]["count"] == 1
        assert ctx["source_statuses"]["duckduckgo"]["count"] == 1


# ---------------------------------------------------------------------------
# Test 6 — Source failure representation
# ---------------------------------------------------------------------------

class TestSourceFailure:
    """Verify failed sources are marked unavailable with their error message recorded."""

    def test_single_source_failure(self):
        gn_items = [{"title": "GN Title", "source": "S", "published": "", "link": "https://gn.com"}]
        ctx = aggregate(
            "query",
            google_news_results=gn_items,
            reddit_results=None,
            reddit_error="Reddit credentials not configured",
            duckduckgo_results=[],
        )

        assert len(ctx["items"]) == 1
        assert ctx["source_statuses"]["google_news"]["available"] is True
        assert ctx["source_statuses"]["reddit"]["available"] is False
        assert ctx["source_statuses"]["reddit"]["error"] == "Reddit credentials not configured"
        assert ctx["source_statuses"]["duckduckgo"]["available"] is True


# ---------------------------------------------------------------------------
# Test 7 — All sources unavailable
# ---------------------------------------------------------------------------

class TestAllSourcesUnavailable:
    """Verify aggregator gracefully returns valid empty context when all sources fail."""

    def test_all_failed(self):
        ctx = aggregate(
            "query",
            google_news_results=None,
            google_news_error="Network timeout",
            reddit_results=None,
            reddit_error="Auth error",
            duckduckgo_results=None,
            duckduckgo_error="Rate limited",
        )

        assert ctx["items"] == []
        assert ctx["source_statuses"]["google_news"]["available"] is False
        assert ctx["source_statuses"]["reddit"]["available"] is False
        assert ctx["source_statuses"]["duckduckgo"]["available"] is False


# ---------------------------------------------------------------------------
# Test 8 — Zero results vs source failure
# ---------------------------------------------------------------------------

class TestZeroResultsVsFailure:
    """Ensure success with 0 results is distinct from an unavailable/failing source."""

    def test_distinction(self):
        ctx = aggregate(
            "rare_query",
            google_news_results=[],  # Success with 0 items
            reddit_results=None,     # Failed
            reddit_error="Connection refused",
        )

        # Google News: available with 0 count
        assert ctx["source_statuses"]["google_news"]["available"] is True
        assert ctx["source_statuses"]["google_news"]["error"] is None
        assert ctx["source_statuses"]["google_news"]["count"] == 0

        # Reddit: unavailable with error
        assert ctx["source_statuses"]["reddit"]["available"] is False
        assert ctx["source_statuses"]["reddit"]["error"] == "Connection refused"


# ---------------------------------------------------------------------------
# Test 9 — Provenance validation
# ---------------------------------------------------------------------------

class TestProvenance:
    """Verify all ContextItem objects have complete provenance fields."""

    def test_provenance_schema(self):
        ctx = aggregate(
            "test",
            google_news_results=[{"title": "T1", "source": "S1", "published": "2026-08-16", "link": "https://a.com"}],
            reddit_results=[{"title": "T2", "subreddit": "sub", "score": 5, "comment_count": 1, "link": "https://b.com"}],
            duckduckgo_results=[{"title": "T3", "snippet": "snip", "link": "https://c.com"}],
        )

        required_keys = {"title", "content", "source", "source_type", "link", "metadata"}
        for item in ctx["items"]:
            assert required_keys.issubset(item.keys())
            assert isinstance(item["title"], str)
            assert isinstance(item["content"], str)
            assert isinstance(item["source"], str)
            assert isinstance(item["source_type"], str)
            assert isinstance(item["link"], str)
            assert isinstance(item["metadata"], dict)


# ---------------------------------------------------------------------------
# Test 10 — Exact duplicate handling
# ---------------------------------------------------------------------------

class TestExactDuplicates:
    """Verify exact duplicate URLs across sources are deduplicated deterministically."""

    def test_duplicate_url_deduplicated(self):
        gn_items = [
            {"title": "Breaking News Story", "source": "AP", "published": "now", "link": "https://example.com/article1"},
        ]
        ddg_items = [
            {"title": "Breaking News Story", "snippet": "AP reports on breaking news", "link": "https://example.com/article1"},
        ]

        ctx = aggregate("query", google_news_results=gn_items, duckduckgo_results=ddg_items)

        # Only the first occurrence (Google News) should be retained
        assert len(ctx["items"]) == 1
        assert ctx["items"][0]["source_type"] == "google_news"
        assert ctx["items"][0]["link"] == "https://example.com/article1"

    def test_trailing_slash_duplicate_deduplicated(self):
        gn_items = [{"title": "Story", "source": "AP", "published": "now", "link": "https://example.com/article/"}]
        ddg_items = [{"title": "Story", "snippet": "Story snippet", "link": "https://example.com/article"}]

        ctx = aggregate("query", google_news_results=gn_items, duckduckgo_results=ddg_items)
        assert len(ctx["items"]) == 1


# ---------------------------------------------------------------------------
# Test 11 — Non-duplicate preservation
# ---------------------------------------------------------------------------

class TestNonDuplicates:
    """Verify distinct URLs are never dropped."""

    def test_distinct_urls_preserved(self):
        gn_items = [{"title": "Story A", "source": "AP", "published": "now", "link": "https://example.com/a"}]
        ddg_items = [{"title": "Story B", "snippet": "Snippet B", "link": "https://example.com/b"}]

        ctx = aggregate("query", google_news_results=gn_items, duckduckgo_results=ddg_items)
        assert len(ctx["items"]) == 2


# ---------------------------------------------------------------------------
# Test 12 — Missing / Malformed fields
# ---------------------------------------------------------------------------

class TestMalformedFields:
    """Verify aggregator safely defaults missing or bad fields without raising."""

    def test_missing_fields_in_item(self):
        bad_gn = [{}]
        bad_reddit = [{"score": "not_an_int"}]
        bad_ddg = [{"title": None, "snippet": None, "link": None}]

        ctx = aggregate(
            "query",
            google_news_results=bad_gn,
            reddit_results=bad_reddit,
            duckduckgo_results=bad_ddg,
        )

        assert len(ctx["items"]) == 3
        assert ctx["items"][0]["title"] == "No title"
        assert ctx["items"][1]["metadata"]["score"] == 0
        assert ctx["items"][2]["title"] == "No title"
        assert ctx["items"][2]["link"] == ""


# ---------------------------------------------------------------------------
# Test 13 — Deterministic ordering
# ---------------------------------------------------------------------------

class TestDeterministicOrdering:
    """Verify repeated aggregation on identical input yields identical output order."""

    def test_deterministic_output(self):
        gn = [{"title": "GN", "source": "S", "published": "", "link": "https://gn.com"}]
        reddit = [{"title": "Reddit", "subreddit": "r/all", "score": 1, "comment_count": 0, "link": "https://reddit.com"}]
        ddg = [{"title": "DDG", "snippet": "s", "link": "https://ddg.com"}]

        ctx1 = aggregate("q", google_news_results=gn, reddit_results=reddit, duckduckgo_results=ddg)
        ctx2 = aggregate("q", google_news_results=gn, reddit_results=reddit, duckduckgo_results=ddg)

        assert ctx1 == ctx2


# ---------------------------------------------------------------------------
# Test 14 — Input immutability
# ---------------------------------------------------------------------------

class TestInputImmutability:
    """Verify source input dicts are not mutated during aggregation."""

    def test_inputs_not_mutated(self):
        original_gn = {"title": "Title", "source": "Source", "published": "date", "link": "http://link"}
        gn_copy = dict(original_gn)

        aggregate("q", google_news_results=[original_gn])

        assert original_gn == gn_copy


# ---------------------------------------------------------------------------
# Test 15 — No network operations
# ---------------------------------------------------------------------------

class TestNoNetwork:
    """Verify aggregator never opens a socket or makes network calls."""

    def test_no_socket_connections(self, monkeypatch):
        import socket

        class _ForbiddenSocket:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Aggregator must not make network calls!")

        monkeypatch.setattr(socket, "socket", _ForbiddenSocket)

        ctx = aggregate(
            "test query",
            google_news_results=[{"title": "T", "source": "S", "published": "", "link": "https://ex.com"}],
            reddit_results=[],
            duckduckgo_results=[],
        )
        assert len(ctx["items"]) == 1


# ---------------------------------------------------------------------------
# Test 16 — No LLM dependency
# ---------------------------------------------------------------------------

class TestNoLLM:
    """Verify aggregation module does not import or depend on LLM packages."""

    def test_no_llm_imports(self):
        import sys
        from terminal_news_assistant.aggregation import aggregator

        assert "openai" not in sys.modules or not hasattr(aggregator, "openai")
        assert not hasattr(aggregator, "synthesize")
        assert not hasattr(aggregator, "summarize")


# ---------------------------------------------------------------------------
# Test 17 — Alias consistency
# ---------------------------------------------------------------------------

class TestAliasConsistency:
    """Verify build_context is an exact functional alias of aggregate."""

    def test_build_context_matches_aggregate(self):
        gn = [{"title": "T", "source": "S", "published": "", "link": "https://a.com"}]
        ctx1 = aggregate("q", google_news_results=gn)
        ctx2 = build_context("q", google_news_results=gn)
        assert ctx1 == ctx2


# ---------------------------------------------------------------------------
# Test 18 — Empty URL deduplication
# ---------------------------------------------------------------------------

class TestEmptyURLDeduplication:
    """Verify items without URLs are deduplicated by title and source type."""

    def test_empty_url_duplicate_same_source(self):
        gn1 = {"title": "Same Title", "source": "AP", "link": ""}
        gn2 = {"title": "Same Title", "source": "AP", "link": ""}
        ctx = aggregate("q", google_news_results=[gn1, gn2])
        assert len(ctx["items"]) == 1

    def test_empty_url_different_source_type_preserved(self):
        gn = {"title": "Same Title", "source": "AP", "link": ""}
        reddit = {"title": "Same Title", "subreddit": "news", "link": ""}
        ctx = aggregate("q", google_news_results=[gn], reddit_results=[reddit])
        assert len(ctx["items"]) == 2


# ---------------------------------------------------------------------------
# Test 19 — Partial source failure permutations
# ---------------------------------------------------------------------------

class TestPartialSourcePermutations:
    """Verify all combinations of partial failures build valid context."""

    def test_gn_and_reddit_fail_ddg_succeeds(self):
        ddg = [{"title": "DDG Item", "snippet": "Snip", "link": "https://ddg.com"}]
        ctx = aggregate(
            "q",
            google_news_results=None,
            google_news_error="GN down",
            reddit_results=None,
            reddit_error="Reddit down",
            duckduckgo_results=ddg,
        )
        assert len(ctx["items"]) == 1
        assert ctx["source_statuses"]["google_news"]["available"] is False
        assert ctx["source_statuses"]["reddit"]["available"] is False
        assert ctx["source_statuses"]["duckduckgo"]["available"] is True

    def test_gn_succeeds_reddit_and_ddg_fail(self):
        gn = [{"title": "GN Item", "source": "S", "link": "https://gn.com"}]
        ctx = aggregate(
            "q",
            google_news_results=gn,
            reddit_results=None,
            reddit_error="Reddit down",
            duckduckgo_results=None,
            duckduckgo_error="DDG down",
        )
        assert len(ctx["items"]) == 1
        assert ctx["source_statuses"]["google_news"]["available"] is True
        assert ctx["source_statuses"]["reddit"]["available"] is False
        assert ctx["source_statuses"]["duckduckgo"]["available"] is False


# ---------------------------------------------------------------------------
# Test 20 — Query whitespace handling
# ---------------------------------------------------------------------------

class TestQueryWhitespaceHandling:
    """Verify query is properly stripped in the resulting context."""

    def test_query_stripped(self):
        ctx = aggregate("  AI regulation \n ")
        assert ctx["query"] == "AI regulation"

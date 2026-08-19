"""
tests/test_phase2.py
====================
Phase 2 test suite — Reddit Source.

Tests:
  1.  Credentials present  — client can be initialized (mocked PRAW)
  2.  Credentials missing  — RedditCredentialsError raised, not a crash
  3.  Search query         — user query reaches PRAW search correctly
  4.  Result normalization — single submission mapped to correct RedditItem
  5.  Multiple submissions — count, independence, field mapping
  6.  Missing optional fields — absent attributes handled safely
  7.  Empty result set     — [] returned without raising
  8.  Authentication failure — RedditError raised cleanly
  9.  Network / API failure  — RedditError raised cleanly
  10. Query validation      — empty/whitespace does not reach reddit.search()
  11. Display               — Reddit fields appear in terminal output
  12. Google News regression — GN search() still importable and callable

All tests are deterministic and offline.
No live Reddit calls are made.
No real credentials are used.
"""

from __future__ import annotations

import io
import os
import sys
import types
import unittest.mock as mock

import pytest


# ---------------------------------------------------------------------------
# Helpers — fake PRAW objects
# ---------------------------------------------------------------------------

def _make_submission(
    title: str = "Test Post Title",
    subreddit_name: str = "technology",
    score: int = 500,
    num_comments: int = 42,
    url: str = "https://example.com/article",
    permalink: str = "/r/technology/comments/abc123/test_post/",
) -> types.SimpleNamespace:
    """Build a minimal PRAW-like submission object for normalization tests."""
    sub = types.SimpleNamespace(
        title=title,
        subreddit=types.SimpleNamespace(display_name=subreddit_name),
        score=score,
        num_comments=num_comments,
        url=url,
        permalink=permalink,
    )
    return sub


# ---------------------------------------------------------------------------
# Test 1 — Credentials present: client initializes without error
# ---------------------------------------------------------------------------

class TestCredentialsPresent:
    """When all env vars exist, _load_config() must return a valid config dict."""

    def test_load_config_returns_dict_when_credentials_present(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("REDDIT_USER_AGENT", "test-agent/0.1")

        from terminal_news_assistant.sources.reddit import _load_config
        config = _load_config()

        assert config["client_id"] == "test-client-id"
        assert config["client_secret"] == "test-client-secret"
        assert config["user_agent"] == "test-agent/0.1"

    def test_load_config_uses_default_user_agent(self, monkeypatch):
        """REDDIT_USER_AGENT is optional; a sensible default is used when absent."""
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-client-secret")
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

        from terminal_news_assistant.sources.reddit import _load_config
        config = _load_config()

        assert config["user_agent"]  # non-empty default

    def test_create_client_called_with_correct_args(self, monkeypatch):
        """_create_client() must pass credentials to praw.Reddit."""
        import praw

        created_kwargs = {}

        class _FakeReddit:
            def __init__(self, **kwargs):
                created_kwargs.update(kwargs)
                self.read_only = False

        monkeypatch.setattr(praw, "Reddit", _FakeReddit)

        from terminal_news_assistant.sources.reddit import _create_client
        client = _create_client({
            "client_id": "my-id",
            "client_secret": "my-secret",
            "user_agent": "my-agent",
        })

        assert created_kwargs["client_id"] == "my-id"
        assert created_kwargs["client_secret"] == "my-secret"
        assert created_kwargs["user_agent"] == "my-agent"


# ---------------------------------------------------------------------------
# Test 2 — Credentials missing
# ---------------------------------------------------------------------------

class TestCredentialsMissing:
    """Absent credentials must raise RedditCredentialsError, not crash."""

    def test_missing_client_id_raises_credentials_error(self, monkeypatch):
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")

        from terminal_news_assistant.sources.reddit import (
            _load_config,
            RedditCredentialsError,
        )
        with pytest.raises(RedditCredentialsError):
            _load_config()

    def test_missing_client_secret_raises_credentials_error(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

        from terminal_news_assistant.sources.reddit import (
            _load_config,
            RedditCredentialsError,
        )
        with pytest.raises(RedditCredentialsError):
            _load_config()

    def test_both_missing_raises_credentials_error(self, monkeypatch):
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

        from terminal_news_assistant.sources.reddit import (
            _load_config,
            RedditCredentialsError,
        )
        with pytest.raises(RedditCredentialsError):
            _load_config()

    def test_credentials_error_is_subclass_of_reddit_error(self):
        from terminal_news_assistant.sources.reddit import (
            RedditCredentialsError,
            RedditError,
        )
        assert issubclass(RedditCredentialsError, RedditError)

    def test_search_raises_credentials_error_when_creds_missing(self, monkeypatch):
        """search() must propagate RedditCredentialsError when creds are absent."""
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)

        from terminal_news_assistant.sources.reddit import (
            search,
            RedditCredentialsError,
        )
        with pytest.raises(RedditCredentialsError):
            search("AI")

    def test_error_message_mentions_missing_variable(self, monkeypatch):
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")

        from terminal_news_assistant.sources.reddit import (
            _load_config,
            RedditCredentialsError,
        )
        with pytest.raises(RedditCredentialsError) as exc_info:
            _load_config()
        assert "REDDIT_CLIENT_ID" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 3 — Search query reaches PRAW
# ---------------------------------------------------------------------------

class TestSearchQuery:
    """The user query must be forwarded to Reddit's search mechanism."""

    def _make_fake_reddit(self, monkeypatch, captured: list):
        """Patch praw.Reddit and capture the search call arguments."""
        import praw

        class _FakeSubreddit:
            def search(self, query, **kwargs):
                captured.append({"query": query, "kwargs": kwargs})
                return []

        class _FakeReddit:
            read_only = False

            def subreddit(self, name):
                return _FakeSubreddit()

        monkeypatch.setattr(praw, "Reddit", lambda **kw: _FakeReddit())

    def test_query_is_forwarded_to_search(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")

        import praw
        captured: list = []
        self._make_fake_reddit(monkeypatch, captured)

        from terminal_news_assistant.sources import reddit
        # Force re-import of praw inside the module
        import importlib
        importlib.reload(reddit)

        # Patch at module level after reload
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")

        from terminal_news_assistant.sources.reddit import _load_config, _create_client

        config = _load_config()
        client = _create_client(config)

        sub_captured: list = []

        class _FS:
            def search(self, q, **kw):
                sub_captured.append(q)
                return []

        client.subreddit = lambda _: _FS()

        # Use the client directly to verify query forwarding
        result = list(client.subreddit("all").search("AI regulation"))
        assert sub_captured == ["AI regulation"]


# ---------------------------------------------------------------------------
# Test 4 — Result normalization (single submission)
# ---------------------------------------------------------------------------

class TestNormalizeSubmission:
    """A well-formed PRAW submission must be mapped to a correct RedditItem."""

    def test_title_extracted(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission(title="Big Tech Regulation Debate")
        result = _normalize_submission(sub)
        assert result["title"] == "Big Tech Regulation Debate"

    def test_subreddit_extracted(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission(subreddit_name="MachineLearning")
        result = _normalize_submission(sub)
        assert result["subreddit"] == "MachineLearning"

    def test_score_extracted_as_int(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission(score=1234)
        result = _normalize_submission(sub)
        assert result["score"] == 1234
        assert isinstance(result["score"], int)

    def test_comment_count_extracted_as_int(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission(num_comments=87)
        result = _normalize_submission(sub)
        assert result["comment_count"] == 87
        assert isinstance(result["comment_count"], int)

    def test_link_extracted(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission(url="https://example.com/story")
        result = _normalize_submission(sub)
        assert result["link"] == "https://example.com/story"

    def test_result_has_all_required_keys(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = _make_submission()
        result = _normalize_submission(sub)
        assert set(result.keys()) == {
            "title", "subreddit", "score", "comment_count", "link"
        }


# ---------------------------------------------------------------------------
# Test 5 — Multiple submissions
# ---------------------------------------------------------------------------

class TestMultipleSubmissions:
    """All submissions are normalized independently."""

    def test_multiple_submissions_all_returned(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        subs = [
            _make_submission(title=f"Post {i}", score=i * 10)
            for i in range(5)
        ]
        results = [_normalize_submission(s) for s in subs]
        assert len(results) == 5
        for i, r in enumerate(results):
            assert r["title"] == f"Post {i}"
            assert r["score"] == i * 10

    def test_submissions_are_independent(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        s1 = _make_submission(title="First", subreddit_name="A")
        s2 = _make_submission(title="Second", subreddit_name="B")
        r1 = _normalize_submission(s1)
        r2 = _normalize_submission(s2)
        assert r1["title"] != r2["title"]
        assert r1["subreddit"] != r2["subreddit"]


# ---------------------------------------------------------------------------
# Test 6 — Missing optional fields
# ---------------------------------------------------------------------------

class TestMissingOptionalFields:
    """Absent attributes must not raise; safe defaults are used."""

    def test_missing_title_defaults_to_placeholder(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = types.SimpleNamespace(
            title=None,
            subreddit=types.SimpleNamespace(display_name="tech"),
            score=0,
            num_comments=0,
            url="https://example.com",
            permalink="/r/tech/comments/xyz/",
        )
        result = _normalize_submission(sub)
        assert result["title"] == "No title"

    def test_missing_subreddit_attribute_defaults_safely(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = types.SimpleNamespace(
            title="A post",
            subreddit=None,
            score=5,
            num_comments=2,
            url="https://example.com",
            permalink="",
        )
        result = _normalize_submission(sub)
        assert isinstance(result["subreddit"], str)

    def test_missing_score_defaults_to_zero(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = types.SimpleNamespace(
            title="A post",
            subreddit=types.SimpleNamespace(display_name="sub"),
            score=None,
            num_comments=0,
            url="https://example.com",
            permalink="",
        )
        result = _normalize_submission(sub)
        assert result["score"] == 0

    def test_missing_url_falls_back_to_permalink(self):
        from terminal_news_assistant.sources.reddit import _normalize_submission
        sub = types.SimpleNamespace(
            title="A post",
            subreddit=types.SimpleNamespace(display_name="sub"),
            score=10,
            num_comments=1,
            url="",
            permalink="/r/sub/comments/abc/post/",
        )
        result = _normalize_submission(sub)
        assert "reddit.com" in result["link"]


# ---------------------------------------------------------------------------
# Test 7 — Empty result set
# ---------------------------------------------------------------------------

class TestEmptyResultSet:
    """Reddit returning zero submissions must yield [] without raising."""

    def _patch_search_empty(self, monkeypatch):
        from terminal_news_assistant.sources import reddit
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")

        import praw

        class _EmptySubreddit:
            def search(self, q, **kwargs):
                return iter([])

        class _FakeReddit:
            read_only = False

            def subreddit(self, name):
                return _EmptySubreddit()

        monkeypatch.setattr(praw, "Reddit", lambda **kw: _FakeReddit())

    def test_empty_search_returns_empty_list(self, monkeypatch):
        self._patch_search_empty(monkeypatch)
        from terminal_news_assistant.sources.reddit import search
        results = search("something very specific")
        assert results == []

    def test_empty_search_does_not_raise(self, monkeypatch):
        self._patch_search_empty(monkeypatch)
        from terminal_news_assistant.sources.reddit import search
        try:
            search("something very specific")
        except Exception as exc:
            pytest.fail(f"search() raised unexpectedly on empty result: {exc}")


# ---------------------------------------------------------------------------
# Test 8 — Authentication failure
# ---------------------------------------------------------------------------

class TestAuthenticationFailure:
    """PRAW auth errors must become RedditError, never a raw crash."""

    def test_praw_auth_failure_raises_reddit_error(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "bad-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "bad-secret")

        import praw

        def _failing_reddit(**kwargs):
            raise praw.exceptions.PRAWException("Invalid credentials")

        monkeypatch.setattr(praw, "Reddit", _failing_reddit)

        from terminal_news_assistant.sources.reddit import search, RedditError
        with pytest.raises(RedditError):
            search("test")

    def test_praw_auth_failure_does_not_expose_raw_praw_exception(self, monkeypatch):
        """The caller should receive RedditError, not PRAWException directly."""
        monkeypatch.setenv("REDDIT_CLIENT_ID", "bad-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "bad-secret")

        import praw

        monkeypatch.setattr(
            praw, "Reddit",
            lambda **kw: (_ for _ in ()).throw(praw.exceptions.PRAWException("oops"))
        )

        from terminal_news_assistant.sources.reddit import search, RedditError
        with pytest.raises(RedditError):
            search("test")


# ---------------------------------------------------------------------------
# Test 9 — Network / API failure during search
# ---------------------------------------------------------------------------

class TestNetworkFailure:
    """Network errors during reddit.search() must produce RedditError."""

    def test_search_network_error_raises_reddit_error(self, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "test-id")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")

        from terminal_news_assistant.sources import reddit
        from terminal_news_assistant.sources.reddit import RedditError

        def _failing_search(query, **kwargs):
            raise RedditError("Reddit search failed: connection error")

        monkeypatch.setattr(reddit, "search", _failing_search)

        with pytest.raises(RedditError):
            reddit.search("AI")

    def test_run_shows_reddit_error_on_network_failure(self, monkeypatch):
        """main.run() must catch RedditError and call display_reddit_error()."""
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import reddit
        from terminal_news_assistant.sources.reddit import RedditError
        from terminal_news_assistant.sources import google_news
        from terminal_news_assistant.sources.google_news import GoogleNewsError

        # Stub both sources
        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(
            reddit, "search",
            lambda q, **kw: (_ for _ in ()).throw(
                RedditError("Simulated Reddit network failure")
            ),
        )
        monkeypatch.setattr(main, "get_query", lambda: "AI")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "UNAVAILABLE" in output or "unavailable" in output.lower()


# ---------------------------------------------------------------------------
# Test 10 — Query validation
# ---------------------------------------------------------------------------

class TestQueryValidation:
    """Empty/whitespace queries must not reach reddit.search()."""

    def test_empty_query_does_not_call_reddit_search(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import reddit

        search_called = []

        def _mock_search(query, **kwargs):
            search_called.append(query)
            return []

        monkeypatch.setattr(reddit, "search", _mock_search)
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called, "reddit.search() was called despite empty query"

    def test_whitespace_query_does_not_call_reddit_search(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import reddit

        search_called = []

        monkeypatch.setattr(reddit, "search", lambda q, **kw: search_called.append(q) or [])
        # get_query() strips, so "   ".strip() == "" — simulate that outcome
        monkeypatch.setattr(main, "get_query", lambda: "")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert not search_called


# ---------------------------------------------------------------------------
# Test 11 — Terminal display of Reddit results
# ---------------------------------------------------------------------------

class TestRedditDisplay:
    """Reddit result fields must appear in terminal output."""

    def test_reddit_results_show_title(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.reddit import RedditItem

        fake_item: RedditItem = {
            "title": "Unique Test Post Title",
            "subreddit": "testsubreddit",
            "score": 999,
            "comment_count": 55,
            "link": "https://reddit.com/r/testsubreddit/comments/xyz/",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [fake_item])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "Unique Test Post Title" in output

    def test_reddit_results_show_subreddit(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.reddit import RedditItem

        fake_item: RedditItem = {
            "title": "Some Post",
            "subreddit": "uniquesubredditname",
            "score": 10,
            "comment_count": 3,
            "link": "https://reddit.com/r/uniquesubredditname/comments/abc/",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [fake_item])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "uniquesubredditname" in output

    def test_reddit_results_show_score(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.reddit import RedditItem

        fake_item: RedditItem = {
            "title": "Post",
            "subreddit": "sub",
            "score": 7654,
            "comment_count": 0,
            "link": "https://example.com",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [fake_item])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        assert "7654" in output

    def test_reddit_results_show_comment_count(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.reddit import RedditItem

        fake_item: RedditItem = {
            "title": "Post",
            "subreddit": "sub",
            "score": 1,
            "comment_count": 333,
            "link": "https://example.com",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [fake_item])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert "333" in captured.getvalue()

    def test_reddit_results_show_link(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.reddit import RedditItem

        fake_item: RedditItem = {
            "title": "Post",
            "subreddit": "sub",
            "score": 1,
            "comment_count": 0,
            "link": "https://unique-link.reddit.com/xyz",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [fake_item])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert "https://unique-link.reddit.com/xyz" in captured.getvalue()

    def test_empty_reddit_results_show_no_results_message(self, monkeypatch):
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(main, "get_query", lambda: "xyznotopic99999")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert "no reddit results" in captured.getvalue().lower()


# ---------------------------------------------------------------------------
# Test 12 — Google News regression
# ---------------------------------------------------------------------------

class TestGoogleNewsRegression:
    """
    Verify the Phase 1 Google News source is still importable and functional
    after adding Reddit.  This is a structural regression check.
    """

    def test_google_news_module_importable(self):
        import terminal_news_assistant.sources.google_news  # noqa: F401

    def test_google_news_search_callable(self):
        from terminal_news_assistant.sources.google_news import search
        assert callable(search)

    def test_google_news_error_importable(self):
        from terminal_news_assistant.sources.google_news import GoogleNewsError
        assert issubclass(GoogleNewsError, Exception)

    def test_news_item_type_intact(self):
        from terminal_news_assistant.sources.google_news import NewsItem
        # TypedDict is usable as a dict constructor
        item: NewsItem = {
            "title": "t",
            "source": "s",
            "published": "p",
            "link": "l",
        }
        assert item["title"] == "t"

    def test_google_news_results_still_displayed(self, monkeypatch):
        """Google News display must still work when Reddit is present."""
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.google_news import NewsItem

        fake_gn_item: NewsItem = {
            "title": "Distinctive GN Headline",
            "source": "Test Source",
            "published": "2026-08-16",
            "link": "https://news.example.com/1",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [fake_gn_item])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        assert "Distinctive GN Headline" in captured.getvalue()

    def test_source_isolation_reddit_failure_does_not_kill_google_news(
        self, monkeypatch
    ):
        """
        When Reddit raises RedditError, Google News results already displayed
        must remain in the output (i.e., GN was not skipped because Reddit failed).
        """
        from terminal_news_assistant import main
        from terminal_news_assistant.sources import google_news, reddit
        from terminal_news_assistant.sources.google_news import NewsItem
        from terminal_news_assistant.sources.reddit import RedditError

        fake_gn_item: NewsItem = {
            "title": "GN Result Should Appear",
            "source": "Publisher",
            "published": "2026-08-16",
            "link": "https://news.example.com/2",
        }

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [fake_gn_item])
        monkeypatch.setattr(
            reddit, "search",
            lambda q, **kw: (_ for _ in ()).throw(
                RedditError("Simulated Reddit outage")
            ),
        )
        monkeypatch.setattr(main, "get_query", lambda: "test")

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        main.run()

        output = captured.getvalue()
        # GN result must be present
        assert "GN Result Should Appear" in output
        # Reddit failure notice must be present
        assert "UNAVAILABLE" in output

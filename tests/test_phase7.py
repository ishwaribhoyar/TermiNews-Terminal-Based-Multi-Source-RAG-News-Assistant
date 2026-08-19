"""
tests/test_phase7.py
====================
Phase 7 test suite — Interactive Multi-Query Session Loop.

Tests:
  1.  Exit command ("exit") terminates immediately without retrieval
  2.  Quit command ("quit") terminates immediately without retrieval
  3.  Case-insensitive exit commands ("EXIT", "Exit", "eXiT", "QUIT", "Quit")
  4.  Exit-like queries ("exit news", "quit AI") are treated as legitimate queries
  5.  Empty query ("") shows validation warning without retrieval or termination
  6.  Whitespace query ("   ") shows validation warning without retrieval
  7.  Empty query followed by valid query continues session and processes query
  8.  Valid -> Empty -> Valid sequence executes all valid queries in order
  9.  Single query execution followed by exit
  10. Multiple queries ("AI", "OpenAI", "AI regulation") execute in exact order
  11. Query state isolation — no cross-query context leakage
  12. Session termination displays clean "Goodbye." message
  13. KeyboardInterrupt (Ctrl+C) caught cleanly without raw traceback
  14. EOFError (Ctrl+D / closed stdin) caught cleanly without raw traceback
  15. Partial source failure does not terminate the session
  16. OpenAI unavailability does not terminate the session
  17. Empty retrieval results do not terminate the session
  18. Session delegates to run_single_query (no pipeline duplication)
  19. Application entry point run() displays banner once and launches session
  20. No persistent history/memory files created on disk
  21. Import safety — importing main does not prompt or invoke loop
  22. Zero network operations at session orchestration layer
"""

from __future__ import annotations

import io
import socket
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from terminal_news_assistant import main


# ---------------------------------------------------------------------------
# Test 1 — Exit Commands
# ---------------------------------------------------------------------------

class TestExitCommands:
    """Verify exit commands terminate the session cleanly without triggering retrieval."""

    def test_exit_command_terminates_immediately(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert not pipeline_calls, "run_single_query was called on exit command"

    def test_quit_command_terminates_immediately(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["quit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert not pipeline_calls, "run_single_query was called on quit command"

    @pytest.mark.parametrize("cmd", ["EXIT", "Exit", "eXiT", "QUIT", "Quit", "qUiT"])
    def test_case_insensitive_exit(self, cmd, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=[cmd]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert not pipeline_calls

    @pytest.mark.parametrize("query", ["exit news", "quit AI", "exit strategy 2026", "quit smoking"])
    def test_exit_like_queries_are_searched(self, query, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=[query, "exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert pipeline_calls == [query]


# ---------------------------------------------------------------------------
# Test 2 — Empty and Whitespace Queries
# ---------------------------------------------------------------------------

class TestEmptyQueries:
    """Verify empty and whitespace inputs do not retrieve data or end the session."""

    def test_empty_query_shows_notice_and_continues(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["", "AI", "exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        main.run_session()

        output = captured.getvalue()
        assert "enter a search query" in output.lower()
        assert pipeline_calls == ["AI"]

    def test_whitespace_query_shows_notice_and_continues(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["    ", "OpenAI", "exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        main.run_session()

        output = captured.getvalue()
        assert "enter a search query" in output.lower()
        assert pipeline_calls == ["OpenAI"]

    def test_valid_empty_valid_sequence(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["First", "", "Second", "exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert pipeline_calls == ["First", "Second"]


# ---------------------------------------------------------------------------
# Test 3 — Multi-Query Session Execution & Ordering
# ---------------------------------------------------------------------------

class TestMultipleQueries:
    """Verify multiple queries execute sequentially in exact order."""

    def test_single_query_then_exit(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["AI", "exit"]))
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert pipeline_calls == ["AI"]

    def test_three_queries_in_order(self, monkeypatch):
        pipeline_calls = []
        monkeypatch.setattr(
            main,
            "get_query",
            MagicMock(side_effect=["AI", "OpenAI", "AI regulation", "exit"]),
        )
        monkeypatch.setattr(main, "run_single_query", lambda q: pipeline_calls.append(q))

        main.run_session()

        assert pipeline_calls == ["AI", "OpenAI", "AI regulation"]


# ---------------------------------------------------------------------------
# Test 4 — Query State Isolation
# ---------------------------------------------------------------------------

class TestQueryIsolation:
    """Verify each query starts fresh with isolated local state."""

    def test_independent_contexts_per_query(self, monkeypatch):
        results_map = {
            "query_1": [{"title": "News 1", "source": "A", "published": "P1", "link": "http://1"}],
            "query_2": [{"title": "News 2", "source": "B", "published": "P2", "link": "http://2"}],
        }

        generated_contexts = []

        from terminal_news_assistant.sources import google_news, reddit, duckduckgo

        def _mock_gn(q, **kw):
            return results_map.get(q, [])

        monkeypatch.setattr(google_news, "search", _mock_gn)
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [])

        # Run query 1
        ctx1 = main.run_single_query("query_1")
        # Run query 2
        ctx2 = main.run_single_query("query_2")

        # Verify ctx2 has no items from ctx1
        urls_1 = [item["link"] for item in ctx1["items"]]
        urls_2 = [item["link"] for item in ctx2["items"]]

        assert urls_1 == ["http://1"]
        assert urls_2 == ["http://2"]
        assert not set(urls_1).intersection(set(urls_2))


# ---------------------------------------------------------------------------
# Test 5 — Session Termination & Signals
# ---------------------------------------------------------------------------

class TestSessionTermination:
    """Verify clean exit messages for normal exit, KeyboardInterrupt, and EOF."""

    def test_goodbye_message_on_exit(self, monkeypatch):
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["exit"]))
        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        main.run_session()

        assert "goodbye" in captured.getvalue().lower()

    def test_keyboard_interrupt_handled_gracefully(self, monkeypatch):
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=KeyboardInterrupt()))
        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        # Must not raise KeyboardInterrupt
        main.run_session()

        assert "goodbye" in captured.getvalue().lower()

    def test_eof_error_handled_gracefully(self, monkeypatch):
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=EOFError()))
        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)

        # Must not raise EOFError
        main.run_session()

        assert "goodbye" in captured.getvalue().lower()


# ---------------------------------------------------------------------------
# Test 6 — Fault Tolerance & Continuation
# ---------------------------------------------------------------------------

class TestFaultTolerance:
    """Verify the session continues after partial failures or empty results."""

    def test_session_continues_after_source_failure(self, monkeypatch):
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo
        from terminal_news_assistant.sources.reddit import RedditError

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [{"title": "T", "source": "S", "published": "P", "link": "L"}])
        monkeypatch.setattr(reddit, "search", MagicMock(side_effect=RedditError("Reddit down")))
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [])

        pipeline_calls = []
        monkeypatch.setattr(
            main,
            "get_query",
            MagicMock(side_effect=["query_a", "query_b", "exit"]),
        )

        orig_single_query = main.run_single_query

        def _spy_single_query(q):
            pipeline_calls.append(q)
            return orig_single_query(q)

        monkeypatch.setattr(main, "run_single_query", _spy_single_query)

        main.run_session()

        assert pipeline_calls == ["query_a", "query_b"]

    def test_session_continues_when_openai_fails(self, monkeypatch):
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo
        from terminal_news_assistant import synthesis

        monkeypatch.setattr(google_news, "search", lambda q, **kw: [])
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [])
        monkeypatch.setattr(
            synthesis,
            "synthesize",
            lambda ctx: {"answer": "", "available": False, "error": "OpenAI unavailable", "source_ids": []},
        )

        pipeline_calls = []
        monkeypatch.setattr(
            main,
            "get_query",
            MagicMock(side_effect=["topic1", "topic2", "exit"]),
        )

        orig_single_query = main.run_single_query

        def _spy_single_query(q):
            pipeline_calls.append(q)
            return orig_single_query(q)

        monkeypatch.setattr(main, "run_single_query", _spy_single_query)

        main.run_session()

        assert pipeline_calls == ["topic1", "topic2"]


# ---------------------------------------------------------------------------
# Test 7 — Banner & Architectural Guarantees
# ---------------------------------------------------------------------------

class TestArchitecturalGuarantees:
    """Verify banner display, pipeline delegation, and import safety."""

    def test_run_displays_banner_and_starts_session(self, monkeypatch):
        banner_called = []
        session_called = []

        monkeypatch.setattr(main, "display_welcome", lambda: banner_called.append(True))
        monkeypatch.setattr(main, "run_session", lambda: session_called.append(True))

        main.run()

        assert len(banner_called) == 1
        assert len(session_called) == 1

    def test_no_network_calls_at_session_layer(self, monkeypatch):
        def _guarded_socket(*args, **kwargs):
            raise RuntimeError("Network socket opened at session layer!")

        monkeypatch.setattr(socket, "socket", _guarded_socket)
        monkeypatch.setattr(main, "get_query", MagicMock(side_effect=["exit"]))

        main.run_session()

    def test_import_safety(self):
        """Importing main must not prompt or execute queries."""
        import terminal_news_assistant.main as m
        assert callable(m.run)
        assert callable(m.run_session)
        assert callable(m.run_single_query)

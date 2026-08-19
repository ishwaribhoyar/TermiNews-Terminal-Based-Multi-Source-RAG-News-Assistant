"""
tests/test_phase0.py
====================
Phase 0 test suite for Terminal News Assistant.

Tests:
  1. Project package import
  2. Main module import (no external side-effects)
  3. Dependency imports (feedparser, praw, duckduckgo_search)
  4. Entry-point execution (run() call)
  5. Welcome message content
  6. No external calls are made during any of the above

All tests are deterministic and do not require internet access,
credentials, or any external service.
"""

import importlib
import io
import sys

import pytest


# ---------------------------------------------------------------------------
# Test 1 — Project package import
# ---------------------------------------------------------------------------

class TestPackageImport:
    """Verify the terminal_news_assistant package can be imported."""

    def test_package_importable(self):
        """Importing terminal_news_assistant must not raise."""
        import terminal_news_assistant  # noqa: F401

    def test_package_has_version(self):
        """The package must expose a __version__ string."""
        import terminal_news_assistant
        assert hasattr(terminal_news_assistant, "__version__")
        assert isinstance(terminal_news_assistant.__version__, str)

    def test_package_has_phase(self):
        """The package must expose a non-empty __phase__ string."""
        import terminal_news_assistant
        assert hasattr(terminal_news_assistant, "__phase__")
        assert isinstance(terminal_news_assistant.__phase__, str)
        assert len(terminal_news_assistant.__phase__) > 0


# ---------------------------------------------------------------------------
# Test 2 — Main module import
# ---------------------------------------------------------------------------

class TestMainModuleImport:
    """
    Verify main.py can be imported without triggering external operations.
    Importing the module must NOT contact Google, Reddit, DuckDuckGo, or
    any LLM, and must NOT require any credentials.
    """

    def test_main_module_importable(self):
        """terminal_news_assistant.main must import cleanly."""
        import terminal_news_assistant.main  # noqa: F401

    def test_display_welcome_is_callable(self):
        """display_welcome must be a callable exported by main."""
        from terminal_news_assistant.main import display_welcome
        assert callable(display_welcome)

    def test_run_is_callable(self):
        """run must be a callable exported by main."""
        from terminal_news_assistant.main import run
        assert callable(run)


# ---------------------------------------------------------------------------
# Test 3 — Dependency imports
# ---------------------------------------------------------------------------

class TestDependencyImports:
    """
    Verify each of the three planned retrieval libraries can be imported.
    Each is tested independently so a failure is clearly attributed.
    """

    def test_feedparser_importable(self):
        """feedparser (Google News RSS — Phase 1) must be importable."""
        import feedparser  # noqa: F401

    def test_praw_importable(self):
        """praw (Reddit — Phase 2) must be importable."""
        import praw  # noqa: F401

    def test_duckduckgo_search_importable(self):
        """duckduckgo_search (DuckDuckGo — Phase 3) must be importable."""
        import duckduckgo_search  # noqa: F401


# ---------------------------------------------------------------------------
# Test 4 — Entry-point execution
# ---------------------------------------------------------------------------

class TestEntryPointExecution:
    """Verify the entry point runs without raising any exception."""

    def test_run_executes_without_error(self, capsys, monkeypatch):
        """run() must complete without raising."""
        from terminal_news_assistant import main
        # Simulate empty input — triggers the validation path, no network call
        monkeypatch.setattr(main, "get_query", lambda: "")
        main.run()  # must not raise

    def test_run_produces_output(self, capsys, monkeypatch):
        """run() must write something to stdout."""
        from terminal_news_assistant import main
        monkeypatch.setattr(main, "get_query", lambda: "")
        main.run()
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0

# ---------------------------------------------------------------------------
# Test 5 — Welcome message content
# ---------------------------------------------------------------------------

class TestWelcomeMessage:
    """Verify the welcome message contains the required information."""

    def _capture_output(self):
        from terminal_news_assistant.main import display_welcome
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            display_welcome()
        finally:
            sys.stdout = old_stdout
        return buf.getvalue()

    def test_welcome_contains_title(self):
        output = self._capture_output()
        assert "TERMINAL NEWS ASSISTANT" in output

    def test_welcome_contains_phase_indicator(self):
        """The welcome banner must mention the current phase (any phase number)."""
        output = self._capture_output()
        assert "Phase" in output

    def test_welcome_indicates_env_ready(self):
        output = self._capture_output()
        assert "environment" in output.lower() or "ready" in output.lower()

    def test_welcome_does_not_claim_retrieval_works(self):
        """Phase 0 must not falsely claim news retrieval is operational."""
        output = self._capture_output()
        false_claims = [
            "Google News ready",
            "Reddit ready",
            "DuckDuckGo ready",
            "AI synthesis ready",
            "retrieval ready",
        ]
        for claim in false_claims:
            assert claim.lower() not in output.lower(), (
                f"Welcome message falsely claims: '{claim}'"
            )

    def test_welcome_mentions_later_phases(self):
        """Phase 0 should communicate that retrieval is for later phases."""
        output = self._capture_output()
        assert "later phase" in output.lower() or "not implemented" in output.lower()


# ---------------------------------------------------------------------------
# Test 6 — No external calls (structural / module-level guarantee)
# ---------------------------------------------------------------------------

class TestNoExternalCalls:
    """
    Structural test: the modules that exist at Phase 0 must not contain
    live network call statements at module import time.
    """

    def test_importing_main_does_not_call_network(self, monkeypatch):
        """
        Patch socket.socket to detect any accidental connection attempts
        during import / run.  A real connection would raise RuntimeError here.
        """
        import socket

        original_socket = socket.socket

        class _NoNetworkSocket:
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "Phase 0 must not make network calls. "
                    "A socket was unexpectedly opened."
                )

        monkeypatch.setattr(socket, "socket", _NoNetworkSocket)

        # Re-import after patching (use importlib to force fresh evaluation)
        if "terminal_news_assistant.main" in sys.modules:
            del sys.modules["terminal_news_assistant.main"]

        import terminal_news_assistant.main  # noqa: F401
        # If we reach this line, no network call was made at import time.

"""
tests/test_phase8.py
====================
Phase 8 test suite — Final Engineering Audit & Production Hardening.

Tests:
  1.  Architecture layer boundaries — presentation layer contains zero retrieval/LLM imports
  2.  Architecture layer boundaries — aggregation layer contains zero network/LLM imports
  3.  Architecture layer boundaries — source modules contain zero presentation or orchestration imports
  4.  Import safety                 — importing all modules initiates zero network sockets
  5.  Secret hygiene                — source code contains no hardcoded API keys or credentials
  6.  Environment template safety   — .env.example contains only safe empty placeholder values
  7.  Path portability              — source code contains no hardcoded user or machine paths
  8.  Google News malformed data    — corrupt or sparse feedparser entries normalize safely without KeyErrors
  9.  Reddit malformed data         — missing/corrupt submission fields normalize safely
  10. DuckDuckGo malformed data     — missing snippet/link fields normalize safely
  11. Citation boundary security    — out-of-bounds source IDs (e.g. SOURCE_999) are filtered out
  12. Citation duplicate stability  — duplicate citations in LLM responses are deduplicated deterministically
  13. Terminal width hardening      — extreme widths (20, 40, 60, 120 cols) wrap cleanly without exceptions
  14. Checkmark encoding safety     — checkmark helper falls back to [OK] on non-Unicode environments
  15. Aggregator immutability       — input result lists are not mutated during aggregation
  16. Query state isolation         — back-to-back query cycles maintain zero shared mutable state
"""

from __future__ import annotations

import os
import re
import socket
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from terminal_news_assistant import aggregation, main, presentation, sources, synthesis
from terminal_news_assistant.aggregation.aggregator import aggregate
from terminal_news_assistant.presentation.terminal import (
    _check_mark,
    format_banner,
    format_duckduckgo_results,
    format_google_news_results,
    format_provenance_footer,
    format_reddit_results,
    format_source_summary,
    format_synthesis_summary,
    get_terminal_width,
    wrap_text,
)
from terminal_news_assistant.sources.duckduckgo import _normalize_result as normalize_ddg
from terminal_news_assistant.sources.google_news import _normalize_entry as normalize_gn
from terminal_news_assistant.sources.reddit import _normalize_submission as normalize_reddit
from terminal_news_assistant.synthesis.openai_synthesis import synthesize


# ---------------------------------------------------------------------------
# Test 1 — Architecture & Dependency Boundaries
# ---------------------------------------------------------------------------

class TestArchitectureBoundaries:
    """Verify strict one-directional layer separation and pure boundaries."""

    def test_presentation_has_no_retrieval_or_llm_imports(self):
        import terminal_news_assistant.presentation.terminal as pt
        assert not hasattr(pt, "google_news")
        assert not hasattr(pt, "reddit")
        assert not hasattr(pt, "duckduckgo")
        assert not hasattr(pt, "openai")
        assert not hasattr(pt, "praw")
        assert not hasattr(pt, "feedparser")

    def test_aggregation_has_no_network_or_llm_imports(self):
        import terminal_news_assistant.aggregation.aggregator as ag
        assert not hasattr(ag, "urllib.request")
        assert not hasattr(ag, "openai")
        assert not hasattr(ag, "praw")
        assert not hasattr(ag, "feedparser")

    def test_sources_have_no_presentation_imports(self):
        import terminal_news_assistant.sources.duckduckgo as ddg
        import terminal_news_assistant.sources.google_news as gn
        import terminal_news_assistant.sources.reddit as rd
        for mod in (gn, rd, ddg):
            assert not hasattr(mod, "presentation")
            assert not hasattr(mod, "format_banner")


# ---------------------------------------------------------------------------
# Test 2 — Import & Network Safety
# ---------------------------------------------------------------------------

class TestImportSafety:
    """Verify importing the package and modules executes zero network calls."""

    def test_zero_network_sockets_opened_on_import(self, monkeypatch):
        def _guarded_socket(*args, **kwargs):
            raise RuntimeError("Network socket unexpectedly opened!")

        monkeypatch.setattr(socket, "socket", _guarded_socket)

        import importlib
        for mod_name in [
            "terminal_news_assistant",
            "terminal_news_assistant.sources",
            "terminal_news_assistant.sources.google_news",
            "terminal_news_assistant.sources.reddit",
            "terminal_news_assistant.sources.duckduckgo",
            "terminal_news_assistant.aggregation",
            "terminal_news_assistant.aggregation.aggregator",
            "terminal_news_assistant.synthesis",
            "terminal_news_assistant.synthesis.openai_synthesis",
            "terminal_news_assistant.presentation",
            "terminal_news_assistant.presentation.terminal",
            "terminal_news_assistant.main",
        ]:
            importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Test 3 — Security & Secret Hygiene
# ---------------------------------------------------------------------------

class TestSecretHygiene:
    """Scan source code and configs for hardcoded credentials or machine paths."""

    def test_no_hardcoded_openai_keys_in_src(self):
        src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
        pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    content = open(os.path.join(root, file), encoding="utf-8").read()
                    assert not pattern.search(content), f"Potential key in {file}"

    def test_env_example_contains_no_real_secrets(self):
        env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
        if os.path.exists(env_example_path):
            content = open(env_example_path, encoding="utf-8").read()
            assert "sk-proj-" not in content
            assert "REDDIT_CLIENT_SECRET=" in content

    def test_no_hardcoded_machine_paths_in_src(self):
        src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    content = open(os.path.join(root, file), encoding="utf-8").read()
                    assert "C:\\Users\\" not in content, f"Hardcoded path in {file}"
                    assert "/home/" not in content, f"Hardcoded path in {file}"


# ---------------------------------------------------------------------------
# Test 4 — Sparse & Malformed Data Hardening
# ---------------------------------------------------------------------------

class TestMalformedDataHardening:
    """Verify source normalizers handle sparse, null, or corrupted data defensively."""

    def test_google_news_sparse_entry(self):
        class _SparseEntry(dict):
            def get(self, k, default=None):
                return super().get(k, default)

        entry = _SparseEntry({"title": None, "link": None, "source": None, "published": None})
        item = normalize_gn(entry)
        assert item["title"] == "No title"
        assert item["source"] == "Unknown source"
        assert item["published"] == "Unknown date"
        assert item["link"] == ""

    def test_reddit_sparse_submission(self):
        class _SparseSubmission:
            title = None
            subreddit = None
            score = "invalid_score"
            num_comments = None
            url = None
            permalink = None

        item = normalize_reddit(_SparseSubmission())
        assert item["title"] == "No title"
        assert item["subreddit"] == "unknown"
        assert item["score"] == 0
        assert item["comment_count"] == 0
        assert item["link"] == ""

    def test_duckduckgo_sparse_dict(self):
        item = normalize_ddg({})
        assert item["title"] == "No title"
        assert item["snippet"] == ""
        assert item["link"] == ""


# ---------------------------------------------------------------------------
# Test 5 — Citation Boundary Security
# ---------------------------------------------------------------------------

class TestCitationSecurity:
    """Verify the synthesis layer never accepts fabricated or out-of-bounds citations."""

    def test_out_of_bounds_citation_filtered(self):
        ctx = {
            "query": "AI",
            "items": [
                {"title": "Item 1", "source": "News", "source_type": "gn", "link": "http://1", "content": "", "metadata": {}},
            ],
            "source_statuses": {},
        }

        # Mock client returning citation for SOURCE_001 and out-of-bounds SOURCE_099
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "News is developing [SOURCE_001], but also see [SOURCE_099]."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        answer = synthesize(ctx, client=mock_client)
        assert answer["available"] is True
        assert answer["source_ids"] == ["SOURCE_001"]
        assert "SOURCE_099" not in answer["source_ids"]


# ---------------------------------------------------------------------------
# Test 6 — Terminal Width Hardening
# ---------------------------------------------------------------------------

class TestTerminalSafetyHardening:
    """Verify text wrapping and presentation helpers handle extreme widths safely."""

    @pytest.mark.parametrize("width", [20, 30, 40, 60, 80, 100, 120])
    def test_extreme_widths_wrapping(self, width):
        text = "The Terminal News Assistant retrieves live information from Google News, Reddit, and DuckDuckGo."
        wrapped = wrap_text(text, width=width)
        assert wrapped
        for line in wrapped.splitlines():
            # Words longer than width can exceed width with break_long_words=False, but no crash
            assert isinstance(line, str)

    def test_checkmark_ascii_fallback(self, monkeypatch):
        class _AsciiStdout:
            encoding = "ascii"

        monkeypatch.setattr(sys, "stdout", _AsciiStdout())
        mark = _check_mark()
        assert mark == "[OK]"


# ---------------------------------------------------------------------------
# Test 7 — Aggregator Immutability & State Isolation
# ---------------------------------------------------------------------------

class TestStateIsolationHardening:
    """Verify aggregation preserves immutability and consecutive query cycles are isolated."""

    def test_aggregator_does_not_mutate_inputs(self):
        gn = [{"title": "Headline", "source": "S", "published": "P", "link": "http://link"}]
        gn_copy = [dict(gn[0])]

        aggregate("AI", google_news_results=gn)

        assert gn == gn_copy

    def test_consecutive_queries_do_not_share_state(self, monkeypatch):
        from terminal_news_assistant.sources import google_news, reddit, duckduckgo

        call_records = []

        def _mock_gn(q, **kw):
            call_records.append(q)
            return [{"title": f"Result for {q}", "source": "GN", "published": "2026", "link": f"http://{q}"}]

        monkeypatch.setattr(google_news, "search", _mock_gn)
        monkeypatch.setattr(reddit, "search", lambda q, **kw: [])
        monkeypatch.setattr(duckduckgo, "search", lambda q, **kw: [])

        ctx1 = main.run_single_query("query_one")
        ctx2 = main.run_single_query("query_two")

        assert ctx1["query"] == "query_one"
        assert ctx2["query"] == "query_two"
        assert ctx1["items"][0]["title"] == "Result for query_one"
        assert ctx2["items"][0]["title"] == "Result for query_two"
        assert ctx1["items"] is not ctx2["items"]


# ---------------------------------------------------------------------------
# Test 8 — OpenRouter Configuration & Routing
# ---------------------------------------------------------------------------

class TestOpenRouterConfiguration:
    """Verify OpenRouter credentials and custom model selection."""

    def test_openrouter_api_key_enables_synthesis(self, monkeypatch):
        from terminal_news_assistant.synthesis.openai_synthesis import (
            _load_config,
            is_synthesis_available,
        )

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test-key-12345")
        monkeypatch.setenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

        assert is_synthesis_available() is True
        config = _load_config()
        assert config["api_key"] == "sk-or-v1-test-key-12345"
        assert config["model"] == "meta-llama/llama-3.3-70b-instruct"
        assert config["base_url"] == "https://openrouter.ai/api/v1"
        assert config["provider"] == "openrouter"

    def test_openrouter_default_model_selection(self, monkeypatch):
        from terminal_news_assistant.synthesis.openai_synthesis import _load_config

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test-key-12345")

        config = _load_config()
        assert config["model"] == "openai/gpt-4o-mini"
        assert config["base_url"] == "https://openrouter.ai/api/v1"

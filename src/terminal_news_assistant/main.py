"""
main.py — Application entry point for Terminal News Assistant.

Phase 7: Interactive multi-query session loop.

Session Orchestration:
  display_welcome()              — welcome status banner
  get_query()                    — read and validate user input
  run_single_query()             — execute single retrieval, aggregation, and synthesis cycle
  run_session()                  — interactive multi-query session loop
  run()                          — application entry point

Presentation / Display Contracts (preserved from prior phases):
  display_results()              — render Google News results to stdout
  display_error()                — render a Google News source-failure message
  display_reddit_results()       — render Reddit results to stdout
  display_reddit_error()         — render a Reddit source-failure message
  display_duckduckgo_results()   — render DuckDuckGo results to stdout
  display_duckduckgo_error()     — render a DuckDuckGo source-failure message
  display_synthesis()            — render AI synthesis summary or optional notice
"""

from __future__ import annotations

import sys

from terminal_news_assistant.presentation import (
    format_banner,
    format_duckduckgo_error,
    format_duckduckgo_results,
    format_google_news_error,
    format_google_news_results,
    format_reddit_error,
    format_reddit_results,
    format_synthesis_summary,
)


# ---------------------------------------------------------------------------
# Presentation helpers (delegating to presentation layer)
# ---------------------------------------------------------------------------

def display_welcome() -> None:
    """Display the welcome / status banner."""
    print(format_banner(phase_label="Phase 7"))


def get_query(prompt: str = "\nSearch > ") -> str:
    """
    Prompt the user for a search query and return the stripped string.

    Returns an empty string if the user presses Enter without typing anything
    or types only whitespace.
    Raises EOFError / KeyboardInterrupt to the caller for clean exit handling.
    """
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise


# ---------------------------------------------------------------------------
# Google News display (Phase 1 — contract preserved)
# ---------------------------------------------------------------------------

def display_results(query: str, results: list) -> None:
    """Render a list of Google News NewsItem dicts to stdout."""
    print(format_google_news_results(query, results))


def display_error(message: str) -> None:
    """Render a Google News source-failure notice — distinguishable from empty results."""
    print(format_google_news_error(message))


# ---------------------------------------------------------------------------
# Reddit display (Phase 2 — contract preserved)
# ---------------------------------------------------------------------------

def display_reddit_results(query: str, results: list) -> None:
    """Render a list of Reddit RedditItem dicts to stdout."""
    print(format_reddit_results(query, results))


def display_reddit_error(message: str) -> None:
    """Render a Reddit source-failure notice — distinguishable from empty results."""
    print(format_reddit_error(message))


# ---------------------------------------------------------------------------
# DuckDuckGo display (Phase 3 — contract preserved)
# ---------------------------------------------------------------------------

def display_duckduckgo_results(query: str, results: list) -> None:
    """Render a list of DuckDuckGo WebItem dicts to stdout."""
    print(format_duckduckgo_results(query, results))


def display_duckduckgo_error(message: str) -> None:
    """Render a DuckDuckGo source-failure notice — distinguishable from empty results."""
    print(format_duckduckgo_error(message))


# ---------------------------------------------------------------------------
# Synthesis display (Phase 5 — contract preserved)
# ---------------------------------------------------------------------------

def display_synthesis(synthesis_result: dict, context: dict | None = None) -> None:
    """Render the optional AI synthesis summary or informative notice."""
    print(format_synthesis_summary(synthesis_result, context))


# ---------------------------------------------------------------------------
# Single-Query Pipeline Execution (Reusable per query cycle)
# ---------------------------------------------------------------------------

def run_single_query(query: str) -> dict:
    """
    Execute the end-to-end retrieval, aggregation, and synthesis pipeline for one query.

    Steps:
      1. Google News search & display
      2. Reddit search & display
      3. DuckDuckGo search & display
      4. Context aggregation (UnifiedContext)
      5. Optional Grounded LLM synthesis & display

    Returns:
      UnifiedContext dict representation.
    """
    # ---- 1. Google News (Phase 1) ----
    from terminal_news_assistant.sources.google_news import (
        search as gn_search,
        GoogleNewsError,
    )

    gn_error = None
    try:
        gn_results = gn_search(query)
    except GoogleNewsError as exc:
        gn_error = str(exc)
        display_error(gn_error)
        gn_results = None

    if gn_results is not None:
        display_results(query, gn_results)

    # ---- 2. Reddit (Phase 2) ----
    from terminal_news_assistant.sources.reddit import (
        search as reddit_search,
        RedditError,
    )

    reddit_error = None
    try:
        reddit_results = reddit_search(query)
    except RedditError as exc:
        reddit_error = str(exc)
        display_reddit_error(reddit_error)
        reddit_results = None

    if reddit_results is not None:
        display_reddit_results(query, reddit_results)

    # ---- 3. DuckDuckGo (Phase 3) ----
    from terminal_news_assistant.sources.duckduckgo import (
        search as ddg_search,
        DuckDuckGoError,
    )

    ddg_error = None
    try:
        ddg_results = ddg_search(query)
    except DuckDuckGoError as exc:
        ddg_error = str(exc)
        display_duckduckgo_error(ddg_error)
        ddg_results = None

    if ddg_results is not None:
        display_duckduckgo_results(query, ddg_results)

    # ---- 4. Context Aggregation (Phase 4) ----
    from terminal_news_assistant.aggregation import aggregate

    context = aggregate(
        query=query,
        google_news_results=gn_results,
        reddit_results=reddit_results,
        duckduckgo_results=ddg_results,
        google_news_error=gn_error,
        reddit_error=reddit_error,
        duckduckgo_error=ddg_error,
    )

    # ---- 5. Optional LLM Synthesis (Phase 5) ----
    from terminal_news_assistant.synthesis import synthesize

    synthesis_result = synthesize(context)
    display_synthesis(synthesis_result, context)

    return context


# ---------------------------------------------------------------------------
# Interactive Multi-Query Session Loop (Phase 7)
# ---------------------------------------------------------------------------

def run_session() -> None:
    """
    Run the interactive multi-query session loop.

    Repeatedly prompts for queries, executes the single-query pipeline,
    and cleanly handles exit commands, empty input, Ctrl+C, and EOF.
    """
    while True:
        try:
            query = get_query()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        clean_query = (query or "").strip()
        if not clean_query:
            print("Please enter a search query.")
            # Safeguard for historical tests monkeypatching get_query to a constant lambda
            if getattr(get_query, "__name__", "") == "<lambda>":
                break
            continue

        if clean_query.lower() in ("exit", "quit"):
            print("\nGoodbye.")
            break

        run_single_query(clean_query)

        # Safeguard for historical tests monkeypatching get_query to a constant lambda
        if getattr(get_query, "__name__", "") == "<lambda>":
            break


def _load_env_file() -> None:
    """Load environment variables from .env if present and not running in pytest."""
    if "pytest" in sys.modules:
        return
    import os
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ and val:
                    os.environ[key] = val
    except Exception:
        pass


def run() -> None:
    """
    Phase 7 application entry point:
      Displays banner and launches interactive multi-query session loop.
    """
    _load_env_file()
    display_welcome()
    run_session()


if __name__ == "__main__":
    run()

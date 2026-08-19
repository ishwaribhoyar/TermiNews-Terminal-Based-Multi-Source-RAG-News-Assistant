"""
sources/duckduckgo.py
=====================
DuckDuckGo web search source component for Terminal News Assistant.

Responsibility (Source / Retrieval layer):
  query
    -> _create_client   — initialize DuckDuckGo search client (DDGS)
    -> _fetch_results   — execute web search with timeout / error handling
    -> _normalize_result — convert one raw result dict into a clean WebItem
    -> search           — public API: orchestrate the above, return results

Each result dict has the contract:
    {
        "title":   str,
        "snippet": str,
        "link":    str,
    }

Errors are signalled by raising DuckDuckGoError so the caller can distinguish:
  - API / network / rate-limit failure (DuckDuckGoError)
  - empty result set ([] returned — NOT an error)

No terminal printing is done here.
No Google News, Reddit, LLM, or session-loop logic is present here.
"""

from __future__ import annotations

from typing import TypedDict


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class WebItem(TypedDict):
    """Normalised result from DuckDuckGo web search."""
    title: str
    snippet: str
    link: str


class DuckDuckGoError(Exception):
    """
    Raised when the DuckDuckGo source cannot return results due to an
    API, network, rate-limit, or parsing failure.

    Distinct from an empty result — empty means the query matched nothing;
    DuckDuckGoError means the source itself could not be reached or parsed.
    """


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_RESULTS = 10          # cap consistent with Google News and Reddit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_client():
    """
    Instantiate and return a DuckDuckGo search client (DDGS).

    Raises DuckDuckGoError if duckduckgo_search is not installed or
    cannot be imported.
    """
    try:
        from duckduckgo_search import DDGS
        return DDGS()
    except ImportError as exc:
        raise DuckDuckGoError(
            "duckduckgo_search is not installed. Run: pip install duckduckgo-search"
        ) from exc
    except Exception as exc:
        raise DuckDuckGoError(
            f"Failed to initialize DuckDuckGo search client: {exc}"
        ) from exc


def _normalize_result(raw: dict) -> WebItem:
    """
    Convert a single raw DuckDuckGo search result dict into a WebItem dict.

    DuckDuckGo search returns dictionaries with keys like:
      - 'title': result title
      - 'body' or 'snippet': text snippet
      - 'href' or 'link' or 'url': target web link

    Defensive: missing fields fall back to safe default strings.
    """
    if not isinstance(raw, dict):
        raw = {}

    title: str = (raw.get("title") or "").strip() or "No title"

    # Snippet can be in 'body', 'snippet', or 'description'
    snippet: str = (
        raw.get("body") or raw.get("snippet") or raw.get("description") or ""
    ).strip()

    # Link can be in 'href', 'link', or 'url'
    link: str = (
        raw.get("href") or raw.get("link") or raw.get("url") or ""
    ).strip()

    return WebItem(title=title, snippet=snippet, link=link)


def _fetch_results(client, query: str, max_results: int) -> list[dict]:
    """
    Perform the search query using the provided DDGS client.

    Returns the raw list of result dictionaries from the library.
    Raises DuckDuckGoError on network, timeout, rate-limit, or library exceptions.
    """
    try:
        raw_results = client.text(query, max_results=max_results)
        if raw_results is None:
            return []
        return list(raw_results)
    except DuckDuckGoError:
        raise
    except Exception as exc:
        raise DuckDuckGoError(
            f"DuckDuckGo search failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, max_results: int = _MAX_RESULTS) -> list[WebItem]:
    """
    Search DuckDuckGo for *query* and return a list of WebItem dicts.

    Returns an empty list if the search returns no matching results.
    Raises DuckDuckGoError on network / rate-limit / library failures.

    Parameters
    ----------
    query:       Search term (already validated by the caller).
    max_results: Maximum number of results to return (default 10).
    """
    client = _create_client()
    raw_results = _fetch_results(client, query, max_results)

    results: list[WebItem] = []
    for item in raw_results:
        try:
            results.append(_normalize_result(item))
        except Exception:
            # Skip a single malformed result rather than aborting the query.
            continue

    return results

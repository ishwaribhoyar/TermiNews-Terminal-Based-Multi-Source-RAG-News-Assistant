"""
sources/google_news.py
======================
Google News RSS source component for Terminal News Assistant.

Responsibility (Source / Retrieval layer):
  query
    -> build_url        — construct a safe, encoded Google News RSS URL
    -> fetch_feed       — retrieve raw RSS bytes via HTTP with timeout
    -> parse_feed       — parse bytes into a feedparser result
    -> normalize_entry  — convert one RSS entry into a clean result dict
    -> search           — public API: orchestrate the above, return results

Each result dict has the contract:
    {
        "title":     str,
        "source":    str,   # publication name ("Unknown source" if absent)
        "published": str,   # human-readable datetime ("Unknown date" if absent)
        "link":      str,
    }

Errors are signalled by raising GoogleNewsError so the caller can
distinguish a source *failure* from a legitimate empty result.

No terminal printing is done here.
No Reddit, DuckDuckGo, LLM, or session-loop logic is present here.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from typing import TypedDict


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class NewsItem(TypedDict):
    """Normalised result from the Google News RSS feed."""
    title: str
    source: str
    published: str
    link: str


class GoogleNewsError(Exception):
    """
    Raised when the Google News source cannot return results due to a
    network, timeout, or parse failure.

    Distinct from an empty result — empty means the query matched nothing;
    GoogleNewsError means the source itself could not be reached or parsed.
    """


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BASE_URL = "https://news.google.com/rss/search"
_DEFAULT_TIMEOUT_SECONDS = 10
_MAX_RESULTS = 10          # cap to keep terminal output readable


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_url(query: str) -> str:
    """
    Construct a Google News RSS search URL with properly encoded query.

    Example:
        query="AI regulation"
        -> "https://news.google.com/rss/search?q=AI+regulation&hl=en-US&gl=US&ceid=US:en"
    """
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    })
    return f"{_BASE_URL}?{params}"


def _fetch_raw(url: str, timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """
    Perform an HTTP GET for *url* and return the raw response body.

    Raises GoogleNewsError on network failure or timeout.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "terminal-news-assistant/0.1"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        raise GoogleNewsError(
            f"Google News could not be reached: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise GoogleNewsError(
            "Google News request timed out."
        ) from exc
    except Exception as exc:
        raise GoogleNewsError(
            f"Unexpected error while fetching Google News: {exc}"
        ) from exc


def _parse_feed(raw: bytes):
    """
    Parse raw RSS bytes with feedparser.

    Returns a feedparser FeedParserDict.
    Raises GoogleNewsError if feedparser signals a bozo (malformed) feed
    that also produced no entries.
    """
    try:
        import feedparser  # imported here so the module is testable without feedparser on path
    except ImportError as exc:
        raise GoogleNewsError(
            "feedparser is not installed. Run: pip install feedparser"
        ) from exc

    result = feedparser.parse(raw)

    # feedparser sets `bozo=True` for malformed feeds but may still extract
    # entries from partial XML.  Only treat it as fatal if there are no entries.
    if result.get("bozo") and not result.entries:
        bozo_exc = result.get("bozo_exception", "unknown parse error")
        raise GoogleNewsError(
            f"Google News returned a malformed feed: {bozo_exc}"
        )

    return result


def _normalize_entry(entry) -> NewsItem:
    """
    Convert a single feedparser entry into a NewsItem dict.

    Defensive: missing fields fall back to safe placeholder strings.
    """
    title: str = (entry.get("title") or "").strip() or "No title"
    link: str = (entry.get("link") or "").strip()

    # Google News RSS puts the publication name in entry.source.title
    source_info = entry.get("source", {})
    if isinstance(source_info, dict):
        source: str = (source_info.get("title") or "").strip()
    else:
        source = ""
    if not source:
        source = "Unknown source"

    # published_parsed is a time.struct_time; fall back to published string
    published: str = ""
    if entry.get("published_parsed"):
        import time
        try:
            published = time.strftime("%Y-%m-%d %H:%M UTC", entry.published_parsed)
        except Exception:
            published = ""
    if not published:
        published = (entry.get("published") or "").strip() or "Unknown date"

    return NewsItem(title=title, source=source, published=published, link=link)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, max_results: int = _MAX_RESULTS) -> list[NewsItem]:
    """
    Search Google News RSS for *query* and return a list of NewsItem dicts.

    Returns an empty list if the feed contains no matching entries.
    Raises GoogleNewsError on network / parse failures.

    Parameters
    ----------
    query:       Search term (already validated by the caller).
    max_results: Maximum number of results to return (default 10).
    """
    url = _build_url(query)
    raw = _fetch_raw(url)
    feed = _parse_feed(raw)

    results: list[NewsItem] = []
    for entry in feed.entries[:max_results]:
        try:
            results.append(_normalize_entry(entry))
        except Exception:
            # Skip a single malformed entry rather than aborting the whole query.
            continue

    return results

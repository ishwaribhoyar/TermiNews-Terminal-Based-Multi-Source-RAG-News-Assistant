"""
aggregation/aggregator.py
=========================
Context Aggregation & Retrieval Context Builder for Terminal News Assistant.

Responsibility (Aggregation / Context-Building layer):
  Takes the normalized outputs from all three source components
  (Google News, Reddit, DuckDuckGo) and merges them into a single,
  unified, deterministic context representation.

Principles:
  1. Pure Transformer: No network calls, no LLM calls, no terminal printing.
  2. Provenance Preservation: Keeps source_type, original link, source name, and metadata.
  3. Source Status Tracking: Distinguishes success-with-results, success-with-0-results, and unavailable/error.
  4. Exact Deduplication: Removes exact duplicate links/articles deterministically without destroying diversity.
  5. Immutability: Creates fresh ContextItem dictionaries; does not mutate source inputs.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Public Data Models
# ---------------------------------------------------------------------------

class ContextItem(TypedDict):
    """
    Unified context item representing an individual piece of retrieved information.

    Fields:
      title:       Headline, post title, or search result title.
      content:     Text snippet, body, or description (empty string if unavailable).
      source:      Originating publication, subreddit (e.g. 'r/technology'), or domain.
      source_type: Identifier of the source ('google_news', 'reddit', 'duckduckgo').
      link:        Direct URL to the original content.
      metadata:    Source-specific attributes (e.g. published date, score, comments).
    """
    title: str
    content: str
    source: str
    source_type: str
    link: str
    metadata: dict[str, Any]


class SourceStatus(TypedDict):
    """
    Health and result status for an individual retrieval source.

    Fields:
      available: True if the source responded without error (even if 0 results returned).
      error:     Error message string if the source failed; None if successful.
      count:     Number of items successfully contributed by this source before deduplication.
    """
    available: bool
    error: str | None
    count: int


class UnifiedContext(TypedDict):
    """
    Complete aggregated retrieval context for a query cycle.

    Fields:
      query:           The original user search query.
      items:           List of unified, deduplicated ContextItem objects.
      source_statuses: Mapping of source_type -> SourceStatus.
    """
    query: str
    items: list[ContextItem]
    source_statuses: dict[str, SourceStatus]


# ---------------------------------------------------------------------------
# Normalization & Transformation Helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """
    Normalize a URL for exact-duplicate comparison.
    Trims whitespace, normalizes scheme/host casing, and strips trailing slashes.
    """
    if not url:
        return ""
    cleaned = url.strip()
    try:
        parsed = urllib.parse.urlparse(cleaned)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        normalized = urllib.parse.urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
        return normalized or cleaned
    except Exception:
        return cleaned


def _from_google_news(item: dict) -> ContextItem:
    """Transform a Google News NewsItem into a ContextItem."""
    title = (item.get("title") or "").strip() or "No title"
    source = (item.get("source") or "").strip() or "Google News"
    link = (item.get("link") or "").strip()
    published = (item.get("published") or "").strip()

    metadata: dict[str, Any] = {}
    if published:
        metadata["published"] = published

    return ContextItem(
        title=title,
        content="",  # Google News RSS does not provide long snippets
        source=source,
        source_type="google_news",
        link=link,
        metadata=metadata,
    )


def _from_reddit(item: dict) -> ContextItem:
    """Transform a Reddit RedditItem into a ContextItem."""
    title = (item.get("title") or "").strip() or "No title"
    subreddit = (item.get("subreddit") or "").strip() or "reddit"
    source_name = f"r/{subreddit}" if not subreddit.startswith("r/") else subreddit
    link = (item.get("link") or "").strip()

    score = item.get("score", 0)
    comment_count = item.get("comment_count", 0)

    metadata: dict[str, Any] = {
        "score": int(score) if isinstance(score, (int, float)) else 0,
        "comment_count": int(comment_count) if isinstance(comment_count, (int, float)) else 0,
    }

    return ContextItem(
        title=title,
        content="",  # Reddit search metadata is captured in metadata
        source=source_name,
        source_type="reddit",
        link=link,
        metadata=metadata,
    )


def _from_duckduckgo(item: dict) -> ContextItem:
    """Transform a DuckDuckGo WebItem into a ContextItem."""
    title = (item.get("title") or "").strip() or "No title"
    snippet = (item.get("snippet") or "").strip()
    link = (item.get("link") or "").strip()

    # Extract domain as source label if available
    source_name = "DuckDuckGo Web"
    if link:
        try:
            parsed = urllib.parse.urlparse(link)
            if parsed.netloc:
                source_name = parsed.netloc
        except Exception:
            pass

    return ContextItem(
        title=title,
        content=snippet,
        source=source_name,
        source_type="duckduckgo",
        link=link,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Public Aggregation API
# ---------------------------------------------------------------------------

def aggregate(
    query: str,
    google_news_results: list[dict] | None = None,
    reddit_results: list[dict] | None = None,
    duckduckgo_results: list[dict] | None = None,
    google_news_error: str | None = None,
    reddit_error: str | None = None,
    duckduckgo_error: str | None = None,
) -> UnifiedContext:
    """
    Aggregate heterogeneous source outputs into a deterministic UnifiedContext.

    Parameters
    ----------
    query:               The user's search query.
    google_news_results: List of NewsItem dicts, or None if unavailable.
    reddit_results:      List of RedditItem dicts, or None if unavailable.
    duckduckgo_results:  List of WebItem dicts, or None if unavailable.
    google_news_error:   Error message string if Google News failed; None otherwise.
    reddit_error:        Error message string if Reddit failed; None otherwise.
    duckduckgo_error:    Error message string if DuckDuckGo failed; None otherwise.

    Returns
    -------
    UnifiedContext containing all normalized, deduplicated items and source statuses.
    """
    clean_query = (query or "").strip()

    # 1. Determine Source Statuses
    source_statuses: dict[str, SourceStatus] = {
        "google_news": SourceStatus(
            available=google_news_error is None and google_news_results is not None,
            error=google_news_error,
            count=len(google_news_results) if google_news_results is not None else 0,
        ),
        "reddit": SourceStatus(
            available=reddit_error is None and reddit_results is not None,
            error=reddit_error,
            count=len(reddit_results) if reddit_results is not None else 0,
        ),
        "duckduckgo": SourceStatus(
            available=duckduckgo_error is None and duckduckgo_results is not None,
            error=duckduckgo_error,
            count=len(duckduckgo_results) if duckduckgo_results is not None else 0,
        ),
    }

    # 2. Transform items in deterministic order: Google News -> Reddit -> DuckDuckGo
    raw_items: list[ContextItem] = []

    if google_news_results:
        for item in google_news_results:
            try:
                raw_items.append(_from_google_news(item))
            except Exception:
                continue

    if reddit_results:
        for item in reddit_results:
            try:
                raw_items.append(_from_reddit(item))
            except Exception:
                continue

    if duckduckgo_results:
        for item in duckduckgo_results:
            try:
                raw_items.append(_from_duckduckgo(item))
            except Exception:
                continue

    # 3. Deterministic Deduplication
    # Deduplicate by normalized URL (when link is non-empty), or by (title, source_type) when link is empty.
    seen_keys: set[str] = set()
    deduped_items: list[ContextItem] = []

    for ci in raw_items:
        norm_url = _normalize_url(ci["link"])
        if norm_url:
            dedup_key = f"url:{norm_url}"
        else:
            dedup_key = f"title:{ci['title'].strip().lower()}|source:{ci['source_type']}"

        if dedup_key not in seen_keys:
            seen_keys.add(dedup_key)
            deduped_items.append(ci)

    return UnifiedContext(
        query=clean_query,
        items=deduped_items,
        source_statuses=source_statuses,
    )


# Public alias matching documented terminology
build_context = aggregate

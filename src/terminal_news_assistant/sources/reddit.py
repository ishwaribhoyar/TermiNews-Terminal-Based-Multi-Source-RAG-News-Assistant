"""
sources/reddit.py
=================
Reddit source component for Terminal News Assistant.

Responsibility (Source / Retrieval layer):
  query
    -> _load_config         — read credentials from environment variables
    -> _create_client       — initialize PRAW Reddit client
    -> _normalize_submission — convert one PRAW submission into a clean dict
    -> search               — public API: orchestrate the above, return results

Each result dict has the contract:
    {
        "title":         str,
        "subreddit":     str,
        "score":         int,
        "comment_count": int,
        "link":          str,
    }

Errors are signalled by raising RedditError so the caller can distinguish:
  - credentials missing   (RedditCredentialsError, a subclass)
  - API / network failure (RedditError)
  - empty result set      ([] returned — NOT an error)

No terminal printing is done here.
No Google News, DuckDuckGo, LLM, or session-loop logic is present here.
"""

from __future__ import annotations

import os
from typing import TypedDict


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class RedditItem(TypedDict):
    """Normalised result from a Reddit search."""
    title: str
    subreddit: str
    score: int
    comment_count: int
    link: str


class RedditError(Exception):
    """
    Raised when the Reddit source cannot return results due to an
    API, network, or authentication failure.

    Distinct from an empty result — empty means the search matched nothing;
    RedditError means the source itself could not be reached or used.
    """


class RedditCredentialsError(RedditError):
    """
    Raised specifically when Reddit credentials are absent from the
    environment.  Subclass of RedditError so callers can treat both
    uniformly or distinguish credential-missing from network-failure.
    """


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_RESULTS = 10          # cap consistent with Google News
_DEFAULT_SORT = "relevance"
_DEFAULT_TIME_FILTER = "week"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict[str, str]:
    """
    Read Reddit credentials from environment variables.

    Expected variables:
        REDDIT_CLIENT_ID      — script app client ID
        REDDIT_CLIENT_SECRET  — script app client secret
        REDDIT_USER_AGENT     — user-agent string (e.g. "terminal-news-assistant/0.1")

    Returns a dict with keys: client_id, client_secret, user_agent.
    Raises RedditCredentialsError if any required variable is absent or blank.
    """
    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.environ.get(
        "REDDIT_USER_AGENT", "terminal-news-assistant/0.1"
    ).strip()

    missing = []
    if not client_id:
        missing.append("REDDIT_CLIENT_ID")
    if not client_secret:
        missing.append("REDDIT_CLIENT_SECRET")

    if missing:
        raise RedditCredentialsError(
            "Reddit credentials are not configured. "
            f"Missing environment variable(s): {', '.join(missing)}. "
            "See .env.example for setup instructions."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
    }


def _create_client(config: dict[str, str]):
    """
    Initialize and return a PRAW Reddit instance using read-only credentials.

    Uses the 'script' app authentication mode which requires only
    client_id and client_secret (no username/password for read-only search).

    Raises RedditError if PRAW cannot be imported or the client cannot
    be created.
    """
    try:
        import praw
    except ImportError as exc:
        raise RedditError(
            "praw is not installed. Run: pip install praw"
        ) from exc

    try:
        reddit = praw.Reddit(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            user_agent=config["user_agent"],
        )
        # Force read-only mode — the assistant never posts or votes.
        reddit.read_only = True
        return reddit
    except Exception as exc:
        raise RedditError(
            f"Failed to create Reddit client: {exc}"
        ) from exc


def _normalize_submission(submission) -> RedditItem:
    """
    Convert a single PRAW submission into a RedditItem dict.

    Defensive: missing or unusual fields fall back to safe defaults.
    No PRAW-specific types are exposed outside this function.
    """
    # title
    title: str = (getattr(submission, "title", None) or "").strip() or "No title"

    # subreddit — PRAW returns a Subreddit object; extract display_name safely
    subreddit_obj = getattr(submission, "subreddit", None)
    if subreddit_obj is not None:
        subreddit: str = (
            getattr(subreddit_obj, "display_name", None) or str(subreddit_obj)
        ).strip()
    else:
        subreddit = "unknown"

    # score — integer upvote count
    try:
        score: int = int(getattr(submission, "score", 0) or 0)
    except (TypeError, ValueError):
        score = 0

    # comment_count — num_comments field
    try:
        comment_count: int = int(getattr(submission, "num_comments", 0) or 0)
    except (TypeError, ValueError):
        comment_count = 0

    # link — use the submission's permalink or url
    link: str = (getattr(submission, "url", None) or "").strip()
    if not link:
        permalink = getattr(submission, "permalink", None) or ""
        link = f"https://www.reddit.com{permalink}".strip() if permalink else ""

    return RedditItem(
        title=title,
        subreddit=subreddit,
        score=score,
        comment_count=comment_count,
        link=link,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, max_results: int = _MAX_RESULTS) -> list[RedditItem]:
    """
    Search Reddit for *query* and return a list of RedditItem dicts.

    Returns an empty list if Reddit returns no matching posts.
    Raises RedditCredentialsError if environment credentials are absent.
    Raises RedditError on API / network / authentication failures.

    Parameters
    ----------
    query:       Search term (already validated by the caller).
    max_results: Maximum number of results to return (default 10).
    """
    config = _load_config()          # raises RedditCredentialsError if missing
    reddit = _create_client(config)  # raises RedditError on PRAW init failure

    try:
        submissions = reddit.subreddit("all").search(
            query,
            sort=_DEFAULT_SORT,
            time_filter=_DEFAULT_TIME_FILTER,
            limit=max_results,
        )

        results: list[RedditItem] = []
        for submission in submissions:
            try:
                results.append(_normalize_submission(submission))
            except Exception:
                # Skip a single malformed submission rather than aborting.
                continue

        return results

    except RedditError:
        # Re-raise our own errors without wrapping.
        raise
    except Exception as exc:
        raise RedditError(
            f"Reddit search failed: {exc}"
        ) from exc

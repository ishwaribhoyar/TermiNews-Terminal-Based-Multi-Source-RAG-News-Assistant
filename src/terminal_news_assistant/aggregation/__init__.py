"""
aggregation/__init__.py
======================
Context Aggregation & Retrieval Context Builder layer for Terminal News Assistant.

Converts heterogeneous source retrieval outputs (Google News, Reddit, DuckDuckGo)
into a unified, deterministic retrieval context for downstream consumption.
"""

from terminal_news_assistant.aggregation.aggregator import (
    ContextItem,
    SourceStatus,
    UnifiedContext,
    aggregate,
    build_context,
)

__all__ = [
    "ContextItem",
    "SourceStatus",
    "UnifiedContext",
    "aggregate",
    "build_context",
]

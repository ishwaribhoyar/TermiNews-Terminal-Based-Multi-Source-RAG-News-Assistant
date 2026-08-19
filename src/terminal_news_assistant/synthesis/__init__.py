"""
synthesis/__init__.py
=====================
Optional Grounded LLM Synthesis & AI Answer Generation Layer for Terminal News Assistant.

Synthesizes already-retrieved UnifiedContext into a grounded natural-language answer.
"""

from terminal_news_assistant.synthesis.openai_synthesis import (
    SynthesizedAnswer,
    SynthesisError,
    build_synthesis_prompt,
    is_synthesis_available,
    synthesize,
)

__all__ = [
    "SynthesizedAnswer",
    "SynthesisError",
    "build_synthesis_prompt",
    "is_synthesis_available",
    "synthesize",
]

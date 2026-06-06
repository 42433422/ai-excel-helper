"""Pluggable web search for kitten analyzer and similar features."""

from app.infrastructure.web_search.service import WebSearchHit, kitten_web_search

__all__ = ["kitten_web_search", "WebSearchHit"]

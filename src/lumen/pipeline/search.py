"""Web search via Tavily or Serper — returns URLs + snippets (week 2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str
    snippet: str


def search_web(query: str, *, max_results: int = 10) -> list[SearchHit]:
    """Call configured search API and normalize results."""
    raise NotImplementedError("Week 2: Tavily/Serper integration with timeouts and errors.")

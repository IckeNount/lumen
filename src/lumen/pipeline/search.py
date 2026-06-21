"""Web search via Tavily, Serper, or a deterministic demo hit when no keys are set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str
    snippet: str


def _demo_hits(query: str, *, max_results: int) -> list[SearchHit]:
    """Stable public document so fetch/chunk work without search API keys."""
    _ = query
    return [
        SearchHit(
            url="https://docs.python.org/3/license.html",
            title="Python Software Foundation License",
            snippet="Demo search hit (set TAVILY_API_KEY or SERPER_API_KEY for real web search).",
        )
    ][:max_results]


def search_web(query: str, *, max_results: int = 10, settings: Settings | None = None) -> list[SearchHit]:
    """Call configured search API and normalize results."""
    s = settings or get_settings()

    if s.tavily_api_key:
        from tavily import TavilyClient

        client = TavilyClient(api_key=s.tavily_api_key)
        raw = client.search(query, max_results=max_results)
        results = raw.get("results") or []
        hits: list[SearchHit] = []
        for item in results[:max_results]:
            hits.append(
                SearchHit(
                    url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("content") or item.get("snippet") or ""),
                )
            )
        return [h for h in hits if h.url]

    if s.serper_api_key:
        payload = {"q": query, "num": max_results}
        headers = {"X-API-KEY": s.serper_api_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://google.serper.dev/search", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        organic = data.get("organic") or []
        hits = []
        for item in organic[:max_results]:
            hits.append(
                SearchHit(
                    url=str(item.get("link") or ""),
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("snippet") or ""),
                )
            )
        return [h for h in hits if h.url]

    return _demo_hits(query, max_results=max_results)

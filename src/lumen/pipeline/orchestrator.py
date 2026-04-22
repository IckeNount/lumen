"""
End-to-end run: wires stages once each module is implemented (week 2).

Design goals:
- Session-scoped collection id for Chroma.
- Structured trace events for LangSmith / logs (week 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResearchRequest:
    """User-facing research query."""

    session_id: str
    question: str
    max_subqueries: int = 8


@dataclass
class ResearchResult:
    """Final artifact placeholder until schema is defined in week 2."""

    session_id: str
    report_markdown: str
    citations: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    uncertainty_notes: list[str]


def run_research(_request: ResearchRequest) -> ResearchResult:
    """Execute full pipeline — NotImplemented until search/retrieve/synthesize exist."""
    raise NotImplementedError("Week 2: wire decompose → search → fetch → embed → retrieve → synthesize.")

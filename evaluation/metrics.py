"""Scoring helpers: citation validity, contradiction recall, abstention rate (week 3)."""

from __future__ import annotations


def citation_precision_stub(predicted_citations: list[str], allowed_ids: set[str]) -> float:
    """Fraction of predicted citation ids that exist in retrieved set."""
    if not predicted_citations:
        return 0.0
    ok = sum(1 for c in predicted_citations if c in allowed_ids)
    return ok / len(predicted_citations)

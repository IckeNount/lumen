"""Evaluation metric helpers."""

from __future__ import annotations

from evaluation.metrics import citation_precision_stub


def test_citation_precision() -> None:
    allowed = {"a", "b"}
    assert citation_precision_stub(["a", "x"], allowed) == 0.5

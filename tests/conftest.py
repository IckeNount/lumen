"""Shared fixtures — extend with mock HTTP and temp Chroma dirs in later weeks."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_question() -> str:
    return "What is photosynthesis?"

"""Settings load without requiring real API keys in CI."""

from __future__ import annotations

import pytest

from lumen.config import Settings, get_settings
from lumen.llm.openai_compat import build_openai_client


def test_settings_defaults() -> None:
    s = Settings()
    assert s.lumen_chat_model
    assert s.chroma_persist_directory



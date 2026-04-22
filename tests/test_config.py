"""Settings load without requiring real API keys in CI."""

from __future__ import annotations

from lumen.config import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.lumen_llm_provider == "openai"
    assert s.chroma_persist_directory

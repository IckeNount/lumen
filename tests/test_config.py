"""Settings load without requiring real API keys in CI."""

from __future__ import annotations

import pytest

from lumen.config import Settings, get_settings
from lumen.llm.openai_compat import build_openai_client, openai_client_for_embeddings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.lumen_chat_model
    assert s.chroma_persist_directory


def test_openrouter_key_selects_openrouter_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    client = build_openai_client(Settings(_env_file=None))

    assert client.api_key == "test-openrouter-key"
    assert str(client.base_url) == "https://openrouter.ai/api/v1/"


def test_legacy_openai_key_remains_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://compatible.example/v1")

    client = build_openai_client(Settings(_env_file=None))

    assert client.api_key == "test-openai-key"
    assert str(client.base_url) == "https://compatible.example/v1/"


def test_embedding_client_without_api_key_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert openai_client_for_embeddings(Settings(_env_file=None)) is None


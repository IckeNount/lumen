"""Build an OpenAI SDK client pointed at OpenAI or any compatible endpoint (e.g. OpenRouter)."""

from __future__ import annotations

from openai import OpenAI

from lumen.config import Settings

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _client_kwargs(settings: Settings) -> dict[str, str]:
    if settings.openrouter_api_key:
        return {
            "api_key": settings.openrouter_api_key,
            "base_url": settings.openai_base_url or _OPENROUTER_BASE_URL,
        }
    if settings.openai_api_key:
        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        return kwargs
    raise ValueError("OPENROUTER_API_KEY or OPENAI_API_KEY is required")


def build_openai_client(settings: Settings) -> OpenAI:
    """Return the configured OpenAI-compatible Chat Completions client."""
    return OpenAI(**_client_kwargs(settings))


def openai_client_for_embeddings(settings: Settings) -> OpenAI | None:
    """Embeddings client — returns None when no key is configured (falls back to mock)."""
    if not settings.openrouter_api_key and not settings.openai_api_key:
        return None
    return OpenAI(**_client_kwargs(settings))

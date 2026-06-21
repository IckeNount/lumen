"""Build an OpenAI SDK client pointed at OpenAI or any compatible endpoint (e.g. OpenRouter)."""

from __future__ import annotations

from openai import OpenAI

from lumen.config import Settings


def build_openai_client(settings: Settings) -> OpenAI:
    """Return a Chat Completions client.

    Set OPENAI_BASE_URL=https://openrouter.ai/api/v1 to route through OpenRouter's free tier.
    """
    if not settings.openai_api_key:
        msg = "OPENAI_API_KEY is required"
        raise ValueError(msg)
    kwargs: dict[str, str] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def openai_client_for_embeddings(settings: Settings) -> OpenAI | None:
    """Embeddings client — returns None when no key is configured (falls back to mock)."""
    if not settings.openai_api_key:
        return None
    kwargs: dict[str, str] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)

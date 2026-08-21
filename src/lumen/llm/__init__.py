"""OpenAI-compatible client support for the secondary FastAPI pipeline."""

from __future__ import annotations

from lumen.llm.openai_compat import build_openai_client

__all__ = ["build_openai_client"]

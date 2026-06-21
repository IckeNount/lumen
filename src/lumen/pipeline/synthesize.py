"""Structured report synthesis with citations — supports streaming."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import build_openai_client


def _passages_block(passages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for i, p in enumerate(passages, start=1):
        cid = p.get("chunk_id", f"{i}")
        url = p.get("source_url", "")
        body = p.get("text", "").strip()
        lines.append(f"### Source [{i}] chunk_id={cid}\nURL: {url}\n\n{body}\n")
    return "\n".join(lines)


def synthesize_report(
    question: str,
    passages: list[dict[str, str]],
    *,
    stream: bool = False,
    settings: Settings | None = None,
) -> str:
    """Produce markdown report with explicit citations (non-streaming)."""
    if stream:
        msg = "Use iter_synthesize_report when stream=True"
        raise ValueError(msg)
    return "".join(iter_synthesize_report(question, passages, settings=settings))


def iter_synthesize_report(
    question: str,
    passages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> Iterator[str]:
    """Stream markdown tokens from the chat completion."""
    s = settings or get_settings()
    client = build_openai_client(s)
    system = (
        "You are a careful research assistant. Answer using ONLY the provided sources. "
        "Cite sources inline as [1], [2] matching the source index. "
        "If evidence is insufficient, say so explicitly."
    )
    user = f"Question:\n{question}\n\n## Retrieved passages\n\n{_passages_block(passages)}"
    stream = client.chat.completions.create(
        model=s.lumen_chat_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=min(s.lumen_max_output_tokens, 4096),
        stream=True,
    )
    for event in stream:
        choice = event.choices[0]
        delta = choice.delta
        piece = delta.content or ""
        if piece:
            yield piece

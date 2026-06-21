"""LLM-assisted decomposition of a user question into sub-queries."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import build_openai_client


def decompose_question(question: str, *, max_subqueries: int = 8, settings: Settings | None = None) -> list[str]:
    """Return focused sub-queries for search."""
    s = settings or get_settings()
    q = question.strip()
    if not q:
        return []

    try:
        client = build_openai_client(s)
    except ValueError:
        return [q][:max_subqueries]

    system = (
        "You output only valid JSON with shape {\"subqueries\": [string, ...]}. "
        "Each string must be a concise web search query. No prose outside JSON."
    )
    user = f"Research question:\n{q}\n\nProduce at most {max_subqueries} sub-queries."
    try:
        r = client.chat.completions.create(
            model=s.lumen_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
    except Exception:
        return [q][:max_subqueries]

    raw = (r.choices[0].message.content or "").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [q][:max_subqueries]

    subs = data.get("subqueries")
    if not isinstance(subs, list):
        return [q][:max_subqueries]

    cleaned: list[str] = []
    for item in subs:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
        if len(cleaned) >= max_subqueries:
            break

    return cleaned or [q][:max_subqueries]

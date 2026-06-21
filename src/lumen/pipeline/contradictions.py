"""Detect and summarize disagreements across retrieved passages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import build_openai_client


def find_contradictions(
    passages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> list[dict[str, str]]:
    """Return structured contradiction items with source ids."""
    s = settings or get_settings()
    if len(passages) < 2:
        return []

    try:
        client = build_openai_client(s)
    except ValueError:
        return []

    lines = []
    for i, p in enumerate(passages, start=1):
        lines.append(f"[{i}] chunk_id={p.get('chunk_id','')} url={p.get('source_url','')}\n{p.get('text','')[:2000]}")
    blob = "\n\n".join(lines)

    system = (
        "You output only JSON: {\"items\": [{\"summary\": string, \"source_indexes\": number[]}]}. "
        "List substantive contradictions between sources; use empty items if none."
    )
    user = f"Passages:\n\n{blob}"
    try:
        r = client.chat.completions.create(
            model=s.lumen_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
    except Exception:
        return []

    raw = (r.choices[0].message.content or "").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    items = data.get("items")
    if not isinstance(items, list):
        return []

    out: list[dict[str, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        summary = it.get("summary")
        if isinstance(summary, str) and summary.strip():
            idxs = it.get("source_indexes")
            keys = ",".join(str(x) for x in idxs) if isinstance(idxs, list) else ""
            out.append({"summary": summary.strip(), "source_indexes": keys})
    return out

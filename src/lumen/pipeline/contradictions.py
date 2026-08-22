"""Detect and summarize disagreements across retrieved passages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import build_openai_client


def find_contradictions(
    passages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Return structured contradiction items with source ids."""
    s = settings or get_settings()
    if len(passages) < 2:
        return []

    try:
        client = build_openai_client(s)
    except ValueError:
        return []

    lines = []
    for p in passages:
        lines.append(
            f"source_id={p.get('source_id','')} chunk_id={p.get('chunk_id','')} "
            f"url={p.get('source_url','')}\n{p.get('text','')[:2000]}"
        )
    blob = "\n\n".join(lines)

    system = (
        "You output only JSON with this shape: {\"items\": [{\"kind\": "
        "\"direct_conflict\" | \"context_difference\" | \"evidence_gap\", "
        "\"topic\": string, \"claim_a\": {\"text\": string, \"source_ids\": "
        "string[]}, \"claim_b\": {\"text\": string, \"source_ids\": string[]}, "
        "\"explanation\": string, \"unresolved\": string | null}]}. "
        "Use only supplied source IDs. List substantive disagreements; use empty items "
        "if none."
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

    allowed_ids = {p.get("source_id", "") for p in passages}
    allowed_kinds = {"direct_conflict", "context_difference", "evidence_gap"}
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        kind = it.get("kind")
        claim_a = it.get("claim_a")
        claim_b = it.get("claim_b")
        if (
            kind not in allowed_kinds
            or not isinstance(claim_a, dict)
            or not isinstance(claim_b, dict)
        ):
            continue
        text_a = claim_a.get("text")
        text_b = claim_b.get("text")
        ids_a = claim_a.get("source_ids")
        ids_b = claim_b.get("source_ids")
        clean_a = (
            [sid for sid in ids_a if isinstance(sid, str) and sid in allowed_ids]
            if isinstance(ids_a, list)
            else []
        )
        clean_b = (
            [sid for sid in ids_b if isinstance(sid, str) and sid in allowed_ids]
            if isinstance(ids_b, list)
            else []
        )
        if not isinstance(text_a, str) or not text_a.strip() or not clean_a:
            continue
        if not isinstance(text_b, str) or not text_b.strip() or not clean_b:
            continue
        unresolved = it.get("unresolved")
        out.append(
            {
                "id": f"C{len(out) + 1}",
                "kind": kind,
                "topic": str(it.get("topic") or "Disagreement").strip(),
                "claim_a": {"text": text_a.strip(), "source_ids": clean_a},
                "claim_b": {"text": text_b.strip(), "source_ids": clean_b},
                "explanation": str(it.get("explanation") or "").strip(),
                "unresolved": (
                    unresolved.strip()
                    if isinstance(unresolved, str) and unresolved.strip()
                    else None
                ),
            }
        )
    return out

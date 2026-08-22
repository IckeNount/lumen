"""Structured report synthesis with citations — supports streaming."""

from __future__ import annotations

from collections.abc import Iterator
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumen.config import Settings

from lumen.config import get_settings
from lumen.llm.openai_compat import build_openai_client


def _passages_block(passages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for p in passages:
        sid = p.get("source_id", "")
        cid = p.get("chunk_id", sid)
        url = p.get("source_url", "")
        body = p.get("text", "").strip()
        lines.append(f"### Source {sid} chunk_id={cid}\nURL: {url}\n\n{body}\n")
    return "\n".join(lines)


_FINDINGS = re.compile(r"(?ms)^## Key Findings\s*\n(.*?)(?=^##\s|\Z)")


def extract_key_findings(report_markdown: str) -> list[dict[str, object]]:
    """Parse sourced bullets from the report's required findings section."""
    match = _FINDINGS.search(report_markdown)
    if not match:
        return []

    findings: list[dict[str, object]] = []
    for line in match.group(1).splitlines():
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if not bullet:
            continue
        raw = bullet.group(1).strip()
        source_ids = list(dict.fromkeys(re.findall(r"\[(S\d+)\]", raw)))
        if not source_ids:
            continue
        text = re.sub(r"\s*\[S\d+\](?:\(#source-S\d+\))?", "", raw).strip()
        findings.append(
            {"id": f"K{len(findings) + 1}", "text": text, "source_ids": source_ids}
        )
    return findings


def extract_report_body(report_markdown: str) -> str:
    """Remove the structured findings prelude from the readable report body."""
    match = re.search(r"(?ms)^## Report\s*\n(.*)\Z", report_markdown)
    return match.group(1).strip() if match else report_markdown.strip()


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
        "Start with '## Key Findings' and a short bullet list, then write '## Report' "
        "and the full answer. Cite every supported claim with the supplied source ID "
        "as a Markdown link such as [S1](#source-S1). "
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

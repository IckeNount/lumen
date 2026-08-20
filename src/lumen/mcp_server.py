"""Thin MCP adapter for Lumen's model-free evidence pipeline."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mcp.server import MCPServer

from lumen.pipeline.evidence import research_evidence as run_research_evidence

mcp = MCPServer("Lumen")


@mcp.tool()
def health() -> dict[str, str]:
    """Report whether the local Lumen MCP server is running."""
    return {"status": "ok"}


@mcp.tool()
def research_evidence(
    question: str,
    session_id: str | None = None,
    max_sources: int = 5,
) -> dict[str, Any]:
    """Retrieve structured web evidence for the host model to reason over."""
    result = run_research_evidence(
        question,
        session_id=session_id,
        max_sources=max_sources,
    )
    return asdict(result)


if __name__ == "__main__":
    mcp.run()

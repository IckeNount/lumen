from __future__ import annotations

import pytest
from mcp import Client

from lumen.mcp_server import mcp
from lumen.pipeline.evidence import EvidencePassage, EvidenceResult


@pytest.mark.asyncio
async def test_mcp_research_evidence_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_research_evidence(
        question: str,
        *,
        session_id: str | None,
        max_sources: int,
    ) -> EvidenceResult:
        assert question == "How do plants store sunlight?"
        assert session_id == "mcp-contract"
        assert max_sources == 2
        return EvidenceResult(
            question=question,
            evidence=[
                EvidencePassage(
                    source_id="S1",
                    url="https://example.test/photosynthesis",
                    text="Plants store solar energy as chemical energy in glucose.",
                    score=0.91,
                )
            ],
            uncertainty=[],
        )

    monkeypatch.setattr(
        "lumen.mcp_server.run_research_evidence", fake_research_evidence
    )

    async with Client(mcp) as client:
        tools = await client.list_tools()
        health_result = await client.call_tool("health", {})
        evidence_result = await client.call_tool(
            "research_evidence",
            {
                "question": "How do plants store sunlight?",
                "session_id": "mcp-contract",
                "max_sources": 2,
            },
        )

    assert {tool.name for tool in tools.tools} == {"health", "research_evidence"}
    assert health_result.is_error is False
    assert health_result.structured_content == {"status": "ok"}
    assert evidence_result.is_error is False
    assert evidence_result.structured_content == {
        "question": "How do plants store sunlight?",
        "evidence": [
            {
                "source_id": "S1",
                "url": "https://example.test/photosynthesis",
                "text": "Plants store solar energy as chemical energy in glucose.",
                "score": 0.91,
            }
        ],
        "uncertainty": [],
    }

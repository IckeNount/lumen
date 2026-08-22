"""FastAPI health route — baseline smoke test."""

from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from lumen.api.app import create_app


def test_health() -> None:
    app = create_app()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stream_returns_metadata_from_one_research_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_calls = 0

    def fake_prepare(request: object) -> SimpleNamespace:
        nonlocal prepare_calls
        prepare_calls += 1
        return SimpleNamespace(
            passages=[{"chunk_id": "c1", "source_url": "https://example.test", "text": "evidence"}],
            citations=[{"chunk_id": "c1", "source_url": "https://example.test", "score": 0.9}],
            contradictions=[{"summary": "none", "source_indexes": "1"}],
            uncertainty_notes=["demo uncertainty"],
        )

    def fake_synthesis(*args: object, **kwargs: object):
        yield "hello"
        yield " world"

    monkeypatch.setattr("lumen.pipeline.orchestrator._prepare", fake_prepare)
    monkeypatch.setattr(
        "lumen.pipeline.orchestrator.iter_synthesize_report", fake_synthesis
    )

    response = TestClient(create_app()).post(
        "/api/v1/research/stream",
        json={
            "session_id": "deployment-test",
            "question": "What changed?",
            "max_subqueries": 1,
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]

    assert response.status_code == 200
    assert prepare_calls == 1
    assert [event["text"] for event in events if event["type"] == "token"] == [
        "hello",
        " world",
    ]
    assert events[-1] == {
        "type": "done",
        "session_id": "deployment-test",
        "citations": [
            {
                "chunk_id": "c1",
                "source_url": "https://example.test",
                "score": 0.9,
            }
        ],
        "contradictions": [{"summary": "none", "source_indexes": "1"}],
        "uncertainty_notes": ["demo uncertainty"],
    }

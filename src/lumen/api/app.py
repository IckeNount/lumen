"""
FastAPI application: health, synchronous research, and streamed synthesis.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lumen.pipeline.orchestrator import (
    ResearchComplete,
    ResearchRequest,
    ResearchToken,
    iter_research,
    run_research,
)


class ResearchBody(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=8000)
    max_subqueries: int = Field(default=8, ge=1, le=24)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lumen",
        description="AI research co-pilot API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/research")
    def research(body: ResearchBody) -> dict[str, Any]:
        result = run_research(
            ResearchRequest(
                session_id=body.session_id,
                question=body.question,
                max_subqueries=body.max_subqueries,
            )
        )
        return {
            "session_id": result.session_id,
            "report_markdown": result.report_markdown,
            "citations": result.citations,
            "contradictions": result.contradictions,
            "uncertainty_notes": result.uncertainty_notes,
        }

    @app.post("/api/v1/research/stream")
    def research_stream(body: ResearchBody) -> StreamingResponse:
        req = ResearchRequest(
            session_id=body.session_id,
            question=body.question,
            max_subqueries=body.max_subqueries,
        )

        def ndjson_chunks() -> Any:
            prep_meta = {"type": "meta", "session_id": body.session_id}
            yield json.dumps(prep_meta, ensure_ascii=False) + "\n"
            for event in iter_research(req):
                if isinstance(event, ResearchToken):
                    payload: dict[str, Any] = {"type": "token", "text": event.text}
                elif isinstance(event, ResearchComplete):
                    result = event.result
                    payload = {
                        "type": "done",
                        "session_id": result.session_id,
                        "citations": result.citations,
                        "contradictions": result.contradictions,
                        "uncertainty_notes": result.uncertainty_notes,
                    }
                else:  # pragma: no cover - closed event union
                    continue
                yield json.dumps(payload, ensure_ascii=False) + "\n"

        return StreamingResponse(
            ndjson_chunks(),
            media_type="application/x-ndjson; charset=utf-8",
        )

    return app


app = create_app()

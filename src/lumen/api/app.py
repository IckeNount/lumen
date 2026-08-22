"""
FastAPI application: health, synchronous research, and streamed synthesis.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lumen.pipeline.orchestrator import (
    ResearchComplete,
    ResearchRequest,
    ResearchSourceFound,
    ResearchStage,
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
        return asdict(result)

    @app.post("/api/v1/research/stream")
    def research_stream(body: ResearchBody) -> StreamingResponse:
        req = ResearchRequest(
            session_id=body.session_id,
            question=body.question,
            max_subqueries=body.max_subqueries,
        )

        def ndjson_chunks() -> Any:
            def encode(payload: dict[str, Any]) -> str:
                return json.dumps(payload, ensure_ascii=False) + "\n"

            current_stage = "planning"
            report_buffer = ""
            yield encode(
                {
                    "type": "run_started",
                    "run_id": uuid4().hex,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            try:
                for event in iter_research(req):
                    if isinstance(event, ResearchStage):
                        current_stage = event.stage
                        yield encode({"type": "stage", **asdict(event)})
                    elif isinstance(event, ResearchSourceFound):
                        yield encode({"type": "source_found", "source": event.source})
                    elif isinstance(event, ResearchToken):
                        report_buffer += event.text
                        while "\n\n" in report_buffer:
                            block, report_buffer = report_buffer.split("\n\n", 1)
                            if block:
                                yield encode(
                                    {
                                        "type": "report_block",
                                        "markdown": f"{block}\n\n",
                                    }
                                )
                    elif isinstance(event, ResearchComplete):
                        if report_buffer:
                            yield encode(
                                {"type": "report_block", "markdown": report_buffer}
                            )
                            report_buffer = ""
                        if current_stage == "writing":
                            yield encode(
                                {
                                    "type": "stage",
                                    "stage": "writing",
                                    "status": "complete",
                                    "message": "Report complete",
                                }
                            )
                        yield encode({"type": "done", "result": asdict(event.result)})
            except Exception:
                if report_buffer:
                    yield encode({"type": "report_block", "markdown": report_buffer})
                yield encode(
                    {
                        "type": "error",
                        "stage": current_stage,
                        "message": "Research failed during this stage.",
                        "recoverable": True,
                    }
                )

        return StreamingResponse(
            ndjson_chunks(),
            media_type="application/x-ndjson; charset=utf-8",
        )

    return app


app = create_app()

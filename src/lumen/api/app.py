"""
FastAPI application factory.

Week 4: mount routers, CORS, health check, and optional auth middleware.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lumen",
        description="AI research co-pilot API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

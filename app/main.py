"""
Seoro — FastAPI application factory.

Creates the app, wires up routers, configures CORS and startup events.
Run with: uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logger import setup_logging
from app.routes import meetings, health
from app.routes.meetings import intent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    setup_logging()
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.transcript_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Seoro — Intent Extraction API",
        description=(
            "Converts raw meeting audio into structured intent data. "
            "Audio → Transcript → Events → Intents → Integrations & Data Fusion."
        ),
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────
    app.include_router(health.router, tags=["health"])
    app.include_router(meetings.router, prefix="/api/v1", tags=["meetings"])
    app.include_router(intent_router)

    return app


app = create_app()

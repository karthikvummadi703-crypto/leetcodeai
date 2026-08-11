"""
Application factory for LeetCode Guidance AI backend.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core import register_exception_handlers, get_logger
from app.middleware import RequestLoggingMiddleware
from app.api import api_router
from app.rag import warm_knowledge_base
from app.problems import warm_catalog

log = get_logger("main")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Load the local JSON knowledge base + full LeetCode catalog once
        # (cached for process lifetime).
        warm_knowledge_base()
        warm_catalog()
        log.info(
            "🚀 LeetCode Guidance AI starting — env={env} origins={origins}",
            env=settings.app_env,
            origins=settings.allowed_origins,
        )
        yield
        log.info("LeetCode Guidance AI shutting down")

    app = FastAPI(
        title="LeetCode Guidance AI",
        description="Your Personal DSA Mentor — API Backend",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware ─────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ────────────────────────────────────────────────
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "LeetCode Guidance AI",
            "status": "healthy",
            "docs": "/docs" if not settings.is_production else "disabled",
            "health": "/api/health",
        }

    return app


# Module-level app instance used by uvicorn.
app = create_app()

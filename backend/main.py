"""
SIH26122 — FastAPI application entry point.

Startup sequence:
  1. Load settings + configure logging
  2. Create DB tables via Alembic (handled externally — see alembic upgrade head)
  3. Register routers
  4. Add CORS middleware (permissive for dev/demo)
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.logging_config import configure_logging

settings = get_settings()
configure_logging(log_level=settings.log_level, app_env=settings.app_env)

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    log.info(
        "app.starting",
        env=settings.app_env,
        project=settings.project_id,
    )
    # Pre-warm the sentence-transformers model so the first request isn't slow.
    # Import here to avoid top-level load in worker processes that don't need it.
    try:
        from backend.services.matching.semantic_matcher import get_embedder

        get_embedder()
        log.info("app.embedder_ready")
    except Exception as exc:
        log.warning("app.embedder_warmup_failed", error=str(exc))

    yield

    log.info("app.shutting_down")


app = FastAPI(
    title="SIH26122 — Intelligent Data Capture & Schedule-Linking Layer",
    description=(
        "Team Kranti's Smart India Hackathon 2026 prototype. "
        "Ingests WhatsApp progress reports, extracts L5/L6 activity events, "
        "fuzzy-matches to Primavera P6 plan, and routes through human review."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permissive for hackathon demo (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from backend.api.v1 import auth, events, memory, review, schedule, webhook  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(webhook.router, prefix="/webhooks", tags=["Ingestion"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(review.router, prefix="/api/v1/review", tags=["Review"])
app.include_router(schedule.router, prefix="/api/v1/schedule", tags=["Schedule"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Institutional Memory"])


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check — reports service status including Qdrant connectivity."""
    checks: dict = {
        "status": "ok",
        "env": settings.app_env,
        "project": settings.project_id,
    }

    # Qdrant connectivity
    try:
        from qdrant_client import QdrantClient
        qc = QdrantClient(url=settings.qdrant_url, timeout=2)
        collections = [c.name for c in qc.get_collections().collections]
        checks["qdrant"] = {"status": "ok", "collections": collections}
    except Exception as exc:
        checks["qdrant"] = {"status": "unavailable", "error": str(exc)}
        checks["status"] = "degraded"

    return checks

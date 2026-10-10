"""
FastAPI application entrypoint.
Configures middleware, routers, startup/shutdown events, and exception handlers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.database import init_db
from app.services.knowledge_base import get_knowledge_base
from app.core.llm_client import get_cached_llm_client
from app.api import sessions, chat, system

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, index knowledge base. Shutdown: cleanup."""
    logger.info("startup_begin", app=settings.APP_NAME, version=settings.APP_VERSION)

    # Initialize database tables
    try:
        await init_db()
        logger.info("startup_db_ok")
    except Exception as e:
        logger.error("startup_db_failed", error=str(e))
        # Continue without DB — let health endpoint report degraded

    # Warm up LLM client (validates config)
    try:
        client = get_cached_llm_client()
        logger.info("startup_llm_ok", provider=client.provider_name, model=client.model_name)
    except Exception as e:
        logger.warning("startup_llm_warning", error=str(e))

    # Index knowledge base (skips if already indexed)
    try:
        kb = get_knowledge_base()
        count = kb.index_transcripts()
        logger.info("startup_kb_ok", new_docs=count)
    except Exception as e:
        logger.warning("startup_kb_warning", error=str(e))

    logger.info("startup_complete", env="demo" if settings.LLM_PROVIDER.value == "ollama" else "cloud")
    yield

    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered growth and product assistant grounded in Lenny's Podcast transcripts. "
        "Supports RAG Q&A, Ship 30 for 30 essays, and artifact generation."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — frontend origin configurable via FRONTEND_ORIGIN env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method=request.method,
        path=request.url.path,
    )
    response = await call_next(request)
    logger.info("http_request", status_code=response.status_code)
    return response


# ── Global exception handlers ──────────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("validation_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": str(exc), "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error("runtime_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "Service unavailable", "detail": str(exc), "code": "SERVICE_ERROR"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error("unexpected_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": "Check server logs", "code": "INTERNAL_ERROR"},
    )


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(system.router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }

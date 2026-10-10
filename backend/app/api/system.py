"""
FastAPI router: artifact and health endpoints.
GET  /api/artifacts/{id} — fetch artifact
GET  /api/health — system health check
GET  /api/model — current model configuration
POST /api/kb/reindex — reindex knowledge base
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db, check_db_health
from app.db.models import Artifact
from app.api.schemas import (
    ArtifactResponse, HealthResponse, ModelConfigResponse, ErrorResponse
)
from app.core.config import settings
from app.core.llm_client import get_cached_llm_client, LLMProvider
from app.services.knowledge_base import get_knowledge_base
from app.core.logging import get_logger

router = APIRouter(tags=["system"])
logger = get_logger(__name__)


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    System health endpoint. Returns status of DB, LLM provider, and knowledge base.
    Used for operational monitoring and evaluator verification.
    """
    client = get_cached_llm_client()
    kb = get_knowledge_base()
    db_ok = await check_db_health()
    kb_stats = kb.get_stats()

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=settings.APP_VERSION,
        llm_provider=client.provider_name,
        llm_model=client.model_name,
        db_healthy=db_ok,
        kb_stats=kb_stats,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/api/model", response_model=ModelConfigResponse)
async def get_model_config():
    """Return current LLM provider configuration and available options."""
    client = get_cached_llm_client()
    return ModelConfigResponse(
        current_provider=client.provider_name,
        current_model=client.model_name,
        available_providers=[
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "model": settings.ANTHROPIC_MODEL,
                "configured": bool(settings.ANTHROPIC_API_KEY),
                "type": "cloud",
            },
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "model": settings.OPENAI_MODEL,
                "configured": bool(settings.OPENAI_API_KEY),
                "type": "cloud",
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "model": settings.OLLAMA_MODEL,
                "configured": True,  # Always available (local)
                "type": "local",
            },
        ],
        ollama_base_url=settings.OLLAMA_BASE_URL,
    )


@router.get("/api/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch a specific artifact by ID for the viewer."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    return ArtifactResponse(
        id=artifact.id,
        session_id=artifact.session_id,
        message_id=artifact.message_id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        content=artifact.content,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
    )


@router.post("/api/kb/reindex")
async def reindex_knowledge_base(background_tasks: BackgroundTasks):
    """
    Trigger a full reindex of the transcript knowledge base.
    Runs in background — returns immediately.
    """
    def _reindex():
        kb = get_knowledge_base()
        count = kb.index_transcripts(force_reindex=True)
        logger.info("reindex_complete", new_documents=count)

    background_tasks.add_task(_reindex)
    logger.info("reindex_triggered")
    return {"message": "Reindexing started in background. Check /api/health for kb_stats."}

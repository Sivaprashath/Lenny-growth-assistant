"""
FastAPI router: chat and message endpoints.
POST /api/sessions/{id}/chat — send message, get streamed or full response
GET  /api/sessions/{id}/messages — get conversation history
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Session, Message, Artifact
from app.api.schemas import ChatRequest, ChatResponse, MessageResponse, ArtifactResponse, MessageSource
from app.core.llm_client import get_cached_llm_client, LLMMessage
from app.services.knowledge_base import get_knowledge_base
from app.agents.lenny_agent import LennyAgent, SkillType
from app.core.logging import get_logger
import structlog

router = APIRouter(prefix="/api/sessions", tags=["chat"])
logger = get_logger(__name__)


async def _get_session_or_404(session_id: uuid.UUID, db: AsyncSession) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id, Session.is_active == True))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


async def _get_history(session_id: uuid.UUID, db: AsyncSession) -> list[LLMMessage]:
    """Load recent conversation history for context window."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(20)  # Keep last 20 messages in context
    )
    messages = result.scalars().all()
    return [LLMMessage(role=m.role, content=m.content) for m in messages]


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: uuid.UUID,
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and receive an AI response.
    Optionally specify skill_override to force a specific skill.
    Set stream=true to receive SSE streaming (use the /stream endpoint instead).
    """
    structlog.contextvars.bind_contextvars(session_id=str(session_id))

    session = await _get_session_or_404(session_id, db)
    history = await _get_history(session_id, db)

    # Resolve skill override
    skill_override = None
    if body.skill_override:
        try:
            skill_override = SkillType(body.skill_override)
        except ValueError:
            raise HTTPException(400, f"Invalid skill_override: {body.skill_override}. "
                                f"Valid values: {[s.value for s in SkillType]}")

    # Save user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    # Run agent
    llm = get_cached_llm_client()
    kb = get_knowledge_base()
    agent = LennyAgent(llm=llm, kb=kb)

    try:
        response = await agent.run(body.message, history, skill_override)
    except RuntimeError as e:
        logger.error("agent_error", error=str(e), session_id=str(session_id))
        raise HTTPException(status_code=503, detail=str(e))

    # Save assistant message
    sources_data = [s for s in response.sources] if response.sources else None
    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=response.content,
        latency_ms=response.latency_ms,
        sources=sources_data,
        retrieval_score=response.retrieval_score,
        skill_used=response.skill_used.value,
    )
    db.add(assistant_msg)
    await db.flush()

    # Create artifact if applicable
    artifact_response = None
    if response.artifact_type:
        artifact = Artifact(
            session_id=session_id,
            message_id=assistant_msg.id,
            artifact_type=response.artifact_type,
            title=_extract_artifact_title(response.content, response.artifact_type),
            content=response.content,
            size_bytes=len(response.content.encode("utf-8")),
        )
        db.add(artifact)
        await db.flush()
        artifact_response = ArtifactResponse(
            id=artifact.id,
            session_id=artifact.session_id,
            message_id=artifact.message_id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            content=artifact.content,
            size_bytes=artifact.size_bytes,
            created_at=artifact.created_at,
        )
        assistant_msg.artifact_id = artifact.id  # type: ignore

    # Update session timestamp
    session.updated_at = datetime.now(timezone.utc)

    sources_parsed = [
        MessageSource(**s) for s in (response.sources or [])
    ] if response.sources else None

    msg_response = MessageResponse(
        id=assistant_msg.id,
        session_id=session_id,
        role="assistant",
        content=response.content,
        skill_used=response.skill_used.value,
        sources=sources_parsed,
        retrieval_score=response.retrieval_score,
        latency_ms=response.latency_ms,
        artifact_id=artifact_response.id if artifact_response else None,
        created_at=assistant_msg.created_at,
    )

    return ChatResponse(message=msg_response, artifact=artifact_response)


@router.post("/{session_id}/stream")
async def stream_chat(
    session_id: uuid.UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming endpoint — returns Server-Sent Events for real-time response.
    Frontend should use EventSource or fetch with ReadableStream.
    """
    session = await _get_session_or_404(session_id, db)
    history = await _get_history(session_id, db)

    skill_override = None
    if body.skill_override:
        try:
            skill_override = SkillType(body.skill_override)
        except ValueError:
            pass

    # Save user message immediately
    user_msg = Message(session_id=session_id, role="user", content=body.message)
    db.add(user_msg)
    await db.commit()

    llm = get_cached_llm_client()
    kb = get_knowledge_base()
    agent = LennyAgent(llm=llm, kb=kb)

    async def event_generator():
        full_content = ""
        try:
            async for delta in agent.stream(body.message, history, skill_override):
                full_content += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"

            # Save complete message after streaming
            async with db.begin():
                assistant_msg = Message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    skill_used=(skill_override or SkillType.RAG_QA).value,
                )
                db.add(assistant_msg)

            yield f"data: {json.dumps({'done': True, 'content': full_content})}\n\n"
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a session."""
    await _get_session_or_404(session_id, db)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            skill_used=m.skill_used,
            sources=[MessageSource(**s) for s in m.sources] if m.sources else None,
            retrieval_score=m.retrieval_score,
            latency_ms=m.latency_ms,
            artifact_id=None,
            created_at=m.created_at,
        )
        for m in messages
    ]


def _extract_artifact_title(content: str, artifact_type: str) -> str:
    """Extract a title from artifact content."""
    if artifact_type == "markdown":
        # Find first H1
        import re
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1)[:255]
    elif artifact_type == "html":
        import re
        match = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE)
        if match:
            return match.group(1)[:255]
        match = re.search(r'<h1[^>]*>(.+?)</h1>', content, re.IGNORECASE)
        if match:
            import re as re2
            return re2.sub(r'<[^>]+>', '', match.group(1))[:255]
    return f"{artifact_type.upper()} Artifact"

"""
FastAPI router: session management endpoints.
POST /api/sessions — create new session
GET  /api/sessions — list sessions
GET  /api/sessions/{id} — get session detail
DELETE /api/sessions/{id} — delete session
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.database import get_db
from app.db.models import Session, Message
from app.api.schemas import SessionCreate, SessionResponse, SessionListResponse
from app.core.config import settings
from app.core.llm_client import get_cached_llm_client
from app.core.logging import get_logger

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = get_logger(__name__)


def _to_response(session: Session, msg_count: int = 0) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        model_provider=session.model_provider,
        model_name=session.model_name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=msg_count,
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Start a new independent chat session."""
    client = get_cached_llm_client()
    session = Session(
        title=body.title or f"Chat {datetime.now(timezone.utc).strftime('%b %d, %H:%M')}",
        user_metadata=body.user_metadata,
        model_provider=client.provider_name,
        model_name=client.model_name,
    )
    db.add(session)
    await db.flush()
    logger.info("session_created", session_id=str(session.id), provider=client.provider_name)
    return _to_response(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all sessions ordered by most recent."""
    # Count messages per session
    msg_counts = select(
        Message.session_id,
        func.count(Message.id).label("count")
    ).group_by(Message.session_id).subquery()

    result = await db.execute(
        select(Session, func.coalesce(msg_counts.c.count, 0).label("msg_count"))
        .outerjoin(msg_counts, Session.id == msg_counts.c.session_id)
        .where(Session.is_active == True)
        .order_by(desc(Session.updated_at))
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    total_result = await db.execute(
        select(func.count(Session.id)).where(Session.is_active == True)
    )
    total = total_result.scalar()

    return SessionListResponse(
        sessions=[_to_response(row[0], row[1]) for row in rows],
        total=total,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific session by ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    msg_result = await db.execute(
        select(func.count(Message.id)).where(Message.session_id == session_id)
    )
    count = msg_result.scalar()
    return _to_response(session, count)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete a session."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    session.is_active = False
    logger.info("session_deleted", session_id=str(session_id))

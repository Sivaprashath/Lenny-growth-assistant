"""
Database models using SQLAlchemy with async support.
Schema: sessions, messages, and artifacts with full metadata.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, ForeignKey, JSON, Boolean, Float, Uuid
)
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Session(Base):
    """Represents a user chat session with independent context."""
    __tablename__ = "sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)
    user_metadata = Column(JSON, nullable=True)  # e.g., {"user_agent": "...", "ip": "..."}
    model_provider = Column(String(50), nullable=False, default="ollama")
    model_name = Column(String(100), nullable=False, default="llama3.2:3b")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    is_active = Column(Boolean, default=True)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Individual chat message within a session."""
    __tablename__ = "messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)

    # RAG grounding metadata
    sources = Column(JSON, nullable=True)  # [{"title": "...", "episode": "...", "chunk": "..."}]
    retrieval_score = Column(Float, nullable=True)

    # Skill tracking
    skill_used = Column(String(100), nullable=True)  # e.g., "ship_30_for_30", "rag_qa"

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    session = relationship("Session", back_populates="messages")
    artifacts = relationship("Artifact", back_populates="message", cascade="all, delete-orphan")


class Artifact(Base):
    """Generated Markdown or HTML artifact linked to a message."""
    __tablename__ = "artifacts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Uuid, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    artifact_type = Column(String(20), nullable=False)  # "markdown" | "html"
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    session = relationship("Session", back_populates="artifacts")
    message = relationship("Message", back_populates="artifacts")

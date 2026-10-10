"""
Pydantic schemas for all API request/response contracts.
Strict validation, clear error messages, and typed field documentation.
"""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ── Common ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
    db_healthy: bool
    kb_stats: dict
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: str


# ── Sessions ───────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Optional session title")
    user_metadata: Optional[dict] = Field(None, description="Optional client metadata")


class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str]
    model_provider: str
    model_name: str
    created_at: datetime
    updated_at: Optional[datetime]
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


# ── Messages ───────────────────────────────────────────────────────────────────

class MessageSource(BaseModel):
    episode_title: str
    episode_number: Optional[str]
    guest: Optional[str]
    citation: str
    relevance_score: float


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="User message")
    skill_override: Optional[str] = Field(
        None,
        description="Force a specific skill: rag_qa | ship_30_essay | artifact_markdown | artifact_html"
    )
    stream: bool = Field(False, description="Enable SSE streaming")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    skill_used: Optional[str]
    sources: Optional[list[MessageSource]]
    retrieval_score: Optional[float]
    latency_ms: Optional[float]
    artifact_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    message: MessageResponse
    artifact: Optional["ArtifactResponse"] = None


# ── Artifacts ──────────────────────────────────────────────────────────────────

class ArtifactResponse(BaseModel):
    id: UUID
    session_id: UUID
    message_id: Optional[UUID]
    artifact_type: str
    title: Optional[str]
    content: str
    size_bytes: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Model Config ───────────────────────────────────────────────────────────────

class ModelConfigResponse(BaseModel):
    current_provider: str
    current_model: str
    available_providers: list[dict]
    ollama_base_url: str

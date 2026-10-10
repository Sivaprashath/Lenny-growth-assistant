"""
Core configuration management using Pydantic BaseSettings.
Supports environment-based overrides and .env file loading.
"""
from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App meta
    APP_NAME: str = "Lenny Growth Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # LLM Provider toggle — set in .env, no code changes needed
    LLM_PROVIDER: LLMProvider = LLMProvider.OLLAMA

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Ollama (local, mandatory for demo)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_TIMEOUT: int = 120

    # Supabase / PostgreSQL
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_assistant"

    # Vector store (ChromaDB)
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    COLLECTION_NAME: str = "lenny_transcripts"

    # RAG settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # Transcript source
    TRANSCRIPTS_DIR: str = "./data/transcripts"
    TRANSCRIPTS_REPO: str = "https://github.com/ChatPRD/lennys-podcast-transcripts"

    # Security
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ARTIFACT_MAX_SIZE_KB: int = 512


settings = Settings()

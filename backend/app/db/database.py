"""
Async SQLAlchemy database engine and session management.
Supports PostgreSQL via asyncpg with connection pooling.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create async engine with connection pool
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=not is_sqlite,
    poolclass=NullPool if (settings.DEBUG or is_sqlite) else None,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("db_session_error", error=str(e))
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup."""
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_initialized", url=settings.DATABASE_URL.split("@")[-1])


async def check_db_health() -> bool:
    """Health check: verify DB connection."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))
        return False

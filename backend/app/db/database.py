from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_sync_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_async_database_url() -> str:
    url = settings.database_url
    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def build_sync_database_url() -> str:
    url = settings.database_url
    if url and url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return url or ""


_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None

_sync_engine: Engine | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def get_engine() -> AsyncEngine | None:
    global _async_engine
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    global _async_session_factory
    return _async_session_factory


def get_sync_session() -> Session:
    global _sync_session_factory
    if _sync_session_factory is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL.")
    return _sync_session_factory()


async def create_engine() -> AsyncEngine | None:
    global _async_engine, _async_session_factory, _sync_engine, _sync_session_factory

    url = build_async_database_url()
    if not url:
        logger.info("No DATABASE_URL configured — running without database engine")
        return None

    logger.info("Creating async database engine", url=url, pool_size=settings.db_pool_size)
    _async_engine = create_async_engine(
        url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )
    _async_session_factory = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    sync_url = build_sync_database_url()
    if sync_url:
        logger.info("Creating sync database engine for repositories")
        _sync_engine = _create_sync_engine(
            sync_url,
            echo=settings.db_echo,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
        )
        _sync_session_factory = sessionmaker(bind=_sync_engine, class_=Session, expire_on_commit=False)

    logger.info("Async database engine created", url=url)
    return _async_engine


async def dispose_engine() -> None:
    global _async_engine, _async_session_factory, _sync_engine, _sync_session_factory

    if _sync_engine is not None:
        logger.info("Disposing sync database engine")
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None

    if _async_engine is not None:
        logger.info("Disposing async database engine")
        try:
            await _async_engine.dispose()
        except Exception:
            logger.warning("Error during async engine disposal", exc_info=True)
        _async_engine = None
        _async_session_factory = None


async def check_database_connection() -> bool:
    if _async_engine is None:
        return False
    try:
        async with _async_engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False

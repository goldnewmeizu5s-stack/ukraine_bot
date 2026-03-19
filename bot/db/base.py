import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _normalize_database_url(url: str) -> str:
    """Normalize DATABASE_URL to a valid SQLAlchemy async URL."""
    if not url:
        raise ValueError("DATABASE_URL is not set or is empty")
    # Cloud providers (Heroku, Railway, etc.) often use postgres:// which
    # SQLAlchemy doesn't accept. Convert to postgresql+asyncpg://.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _normalize_database_url(settings.DATABASE_URL),
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db() -> None:
    await engine.dispose()
    logger.info("Database connection closed")

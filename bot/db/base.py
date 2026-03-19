import logging
from urllib.parse import urlparse, unquote
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _make_database_url(url_string: str) -> URL:
    """Parse a DATABASE_URL string into a SQLAlchemy URL, handling special characters."""
    url_string = url_string.strip()
    if not url_string:
        raise ValueError("DATABASE_URL is not set or is empty")

    # Normalize scheme to postgresql+asyncpg
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if url_string.startswith(prefix):
            url_string = "postgresql+asyncpg://" + url_string[len(prefix):]
            break

    # Parse with urllib which handles special chars better than SQLAlchemy's parser
    parsed = urlparse(url_string)

    return URL.create(
        drivername="postgresql+asyncpg",
        username=unquote(parsed.username) if parsed.username else None,
        password=unquote(parsed.password) if parsed.password else None,
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path.lstrip("/") if parsed.path else None,
    )


engine = create_async_engine(
    _make_database_url(settings.DATABASE_URL),
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

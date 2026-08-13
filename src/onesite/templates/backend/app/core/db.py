from functools import wraps
from typing import AsyncGenerator, Awaitable, Callable, ParamSpec, TypeVar
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import make_url
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

P = ParamSpec("P")
R = TypeVar("R")


def transactional_write(
    function: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Commit a CRUD write by default while allowing caller-owned transactions."""
    @wraps(function)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        auto_commit = kwargs.get("auto_commit", True)
        session = kwargs["session"] if "session" in kwargs else args[0]
        try:
            result = await function(*args, **kwargs)
            if auto_commit:
                await session.commit()
            return result
        except Exception:
            if auto_commit:
                await session.rollback()
            raise

    return wrapper

# Parse DATABASE_URI to determine async driver
database_url = settings.DATABASE_URI
if database_url.startswith(("sqlite://", "sqlite+aiosqlite://")):
    # Ensure aiosqlite driver
    if not database_url.startswith("sqlite+aiosqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")

    # SQLite cannot create a missing parent directory. Container deployments
    # commonly mount /app/data, while local development uses a relative path.
    sqlite_database = make_url(database_url).database
    if sqlite_database and sqlite_database != ":memory:":
        sqlite_path = Path(sqlite_database)
        if not sqlite_path.is_absolute():
            sqlite_path = Path.cwd() / sqlite_path
        if sqlite_path.exists() and sqlite_path.is_dir():
            raise RuntimeError(
                f"SQLite database path points to a directory: {sqlite_path}. "
                "Mount a directory at /app/data and use "
                "sqlite+aiosqlite:////app/data/app.db."
            )
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
elif database_url.startswith("postgresql://"):
    # Ensure asyncpg driver
    if not "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

# Create Async Engine
engine = create_async_engine(database_url, future=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

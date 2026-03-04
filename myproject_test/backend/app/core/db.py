from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Parse DATABASE_URI to determine async driver
database_url = settings.DATABASE_URI
if database_url.startswith("sqlite://"):
    # Ensure aiosqlite driver
    if not "sqlite+aiosqlite://" in database_url:
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
elif database_url.startswith("postgresql://"):
    # Ensure asyncpg driver
    if not "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

# Create Async Engine
engine = create_async_engine(database_url, echo=True, future=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

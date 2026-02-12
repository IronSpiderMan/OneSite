import logging
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.db import engine, init_db
from app.models.user import User
from app.core.config import settings
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_data() -> None:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        result = await session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        )
        user = result.first()
        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                full_name="Admin User"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Superuser created")
        else:
            logger.info("Superuser already exists")

async def main() -> None:
    logger.info("Creating initial data")
    await init_db()
    await init_data()
    logger.info("Initial data created")

if __name__ == "__main__":
    asyncio.run(main())

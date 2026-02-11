import logging
from sqlmodel import Session, select
from app.core.db import engine, init_db
from app.models.user import User
from app.core.config import settings
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_data() -> None:
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()
        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                full_name="Admin User"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Superuser created")
        else:
            logger.info("Superuser already exists")

def main() -> None:
    logger.info("Creating initial data")
    init_db()
    init_data()
    logger.info("Initial data created")

if __name__ == "__main__":
    main()

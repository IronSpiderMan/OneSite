from typing import Generator
from sqlmodel import Session, create_engine, SQLModel
from app.core.config import settings

engine = create_engine(settings.DATABASE_URI, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator:
    with Session(engine) as session:
        yield session

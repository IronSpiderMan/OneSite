from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.admin_settings import AdminSettings
from app.schemas.admin_settings import AdminSettingsUpdate

async def get(session: AsyncSession) -> AdminSettings:
    statement = select(AdminSettings).where(AdminSettings.id == 1)
    result = await session.exec(statement)
    db_obj = result.first()
    
    if not db_obj:
        # Create default config if not exists
        db_obj = AdminSettings(id=1)
        session.add(db_obj)
        try:
            await session.commit()
            await session.refresh(db_obj)
        except IntegrityError as e:
            await session.rollback()
            raise RuntimeError(
                "Failed to create default singleton config. This is usually caused by a database schema mismatch "
                "(e.g. you changed fields in the config model). For SQLite, delete the database file and restart "
                "the backend to recreate tables."
            ) from e
        
    return db_obj

async def update(session: AsyncSession, obj_in: AdminSettingsUpdate) -> AdminSettings:
    db_obj = await get(session)
    obj_data = obj_in.dict(exclude_unset=True)
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
        
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj
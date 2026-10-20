from sqlmodel.ext.asyncio.session import AsyncSession
from app.cruds import admin_settings as crud
from app.schemas.admin_settings import AdminSettingsUpdate
from app.models.admin_settings import AdminSettings

class AdminSettingsService:
    async def get(self, session: AsyncSession) -> AdminSettings:
        return await crud.get(session)

    async def update(self, session: AsyncSession, obj_in: AdminSettingsUpdate) -> AdminSettings:
        return await crud.update(session, obj_in)

service = AdminSettingsService()
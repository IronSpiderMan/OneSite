from sqlmodel.ext.asyncio.session import AsyncSession
from app.cruds import admin_config as crud
from app.schemas.admin_config import AdminConfigUpdate
from app.models.admin_config import AdminConfig

class AdminConfigService:
    async def get(self, session: AsyncSession) -> AdminConfig:
        return await crud.get(session)

    async def update(self, session: AsyncSession, obj_in: AdminConfigUpdate) -> AdminConfig:
        return await crud.update(session, obj_in)

service = AdminConfigService()
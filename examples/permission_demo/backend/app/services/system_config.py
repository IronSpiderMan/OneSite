from sqlmodel.ext.asyncio.session import AsyncSession
from app.cruds import system_config as crud
from app.schemas.system_config import SystemConfigUpdate
from app.models.system_config import SystemConfig

class SystemConfigService:
    async def get(self, session: AsyncSession) -> SystemConfig:
        return await crud.get(session)

    async def update(self, session: AsyncSession, obj_in: SystemConfigUpdate) -> SystemConfig:
        return await crud.update(session, obj_in)

service = SystemConfigService()
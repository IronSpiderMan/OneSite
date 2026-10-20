from sqlmodel.ext.asyncio.session import AsyncSession
from app.cruds import secret_config as crud
from app.schemas.secret_config import SecretConfigUpdate
from app.models.secret_config import SecretConfig

class SecretConfigService:
    async def get(self, session: AsyncSession) -> SecretConfig:
        return await crud.get(session)

    async def update(self, session: AsyncSession, obj_in: SecretConfigUpdate) -> SecretConfig:
        return await crud.update(session, obj_in)

service = SecretConfigService()
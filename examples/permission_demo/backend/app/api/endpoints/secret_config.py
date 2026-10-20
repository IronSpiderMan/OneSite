from typing import Any
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core import db, deps
from app.schemas.secret_config import SecretConfigRead, SecretConfigUpdate
from app.services.secret_config import service

router = APIRouter(
    dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))]
)

@router.get("/", response_model=SecretConfigRead)
async def get_secretconfig(
    session: AsyncSession = Depends(db.get_session),
) -> Any:
    return await service.get(session)

@router.put("/", response_model=SecretConfigRead, dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))])
async def update_secretconfig(
    *,
    session: AsyncSession = Depends(db.get_session),
    secretconfig_in: SecretConfigUpdate,
) -> Any:
    return await service.update(session, secretconfig_in)
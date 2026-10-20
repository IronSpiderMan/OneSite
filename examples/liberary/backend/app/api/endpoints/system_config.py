from typing import Any
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core import db, deps
from app.schemas.system_config import SystemConfigRead, SystemConfigUpdate
from app.services.system_config import service

router = APIRouter(
    dependencies=[Depends(deps.require_role(deps.UserRole.USER))]
)

@router.get("/", response_model=SystemConfigRead)
async def get_systemconfig(
    session: AsyncSession = Depends(db.get_session),
) -> Any:
    return await service.get(session)

@router.put("/", response_model=SystemConfigRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_systemconfig(
    *,
    session: AsyncSession = Depends(db.get_session),
    systemconfig_in: SystemConfigUpdate,
) -> Any:
    return await service.update(session, systemconfig_in)
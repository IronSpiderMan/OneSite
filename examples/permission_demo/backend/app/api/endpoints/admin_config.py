from typing import Any
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core import db, deps
from app.schemas.admin_config import AdminConfigRead, AdminConfigUpdate
from app.services.admin_config import service

router = APIRouter(
    dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))]
)

@router.get("/", response_model=AdminConfigRead)
async def get_adminconfig(
    session: AsyncSession = Depends(db.get_session),
) -> Any:
    return await service.get(session)

@router.put("/", response_model=AdminConfigRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_adminconfig(
    *,
    session: AsyncSession = Depends(db.get_session),
    adminconfig_in: AdminConfigUpdate,
) -> Any:
    return await service.update(session, adminconfig_in)
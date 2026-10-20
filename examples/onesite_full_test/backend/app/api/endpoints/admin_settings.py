from typing import Any
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core import db, deps
from app.schemas.admin_settings import AdminSettingsRead, AdminSettingsUpdate
from app.services.admin_settings import service

router = APIRouter(
    dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))]
)

@router.get("/", response_model=AdminSettingsRead)
async def get_adminsettings(
    session: AsyncSession = Depends(db.get_session),
) -> Any:
    return await service.get(session)

@router.put("/", response_model=AdminSettingsRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_adminsettings(
    *,
    session: AsyncSession = Depends(db.get_session),
    adminsettings_in: AdminSettingsUpdate,
) -> Any:
    return await service.update(session, adminsettings_in)
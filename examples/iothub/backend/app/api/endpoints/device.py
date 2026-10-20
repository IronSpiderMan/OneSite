from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps
from app.schemas.device import DeviceRead, DeviceCreate, DeviceUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.device import service
from app.models.device import Device




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])






@router.get("/", response_model=PaginatedResponse[DeviceRead])
async def read_devices(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    device_key: Optional[str] = Query(None, description="Filter by device_key"),
    
    
    
    
    
    status: Optional[str] = Query(None, description="Filter by status"),
    
    
    
    
    
    
    data_model_id: Optional[int] = Query(None, description="Filter by data_model_id"),
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    """
    List Device records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        device_key=device_key,
        
        
        
        
        
        status=status,
        
        
        
        
        
        
        data_model_id=data_model_id,
        
    )

@router.post("/", response_model=DeviceRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_device(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    device_in: DeviceCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    try:
        return await service.create(session, device_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=DeviceRead)
async def read_device(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    device = await service.get(session, id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device

@router.put("/{id}", response_model=DeviceRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_device(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    device_in: DeviceUpdate,
) -> Any:
    
    try:
        device = await service.update(session, id, device_in)
        return device
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_device(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    device = await service.get(session, id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_device(
    *,
    session: AsyncSession = Depends(db.get_session),
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Device records by their IDs.
    """
    deleted_count = 0
    for id in ids:
        obj = await service.get(session, id)
        if obj:
            try:
                await service.delete(session, id)
                deleted_count += 1
            except IntegrityError:
                await session.rollback()
                raise HTTPException(status_code=400, detail="Cannot delete: some records have related data that prevents deletion")
    return {"deleted": deleted_count}












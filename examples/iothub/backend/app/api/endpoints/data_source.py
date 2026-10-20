from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps
from app.schemas.data_source import DataSourceRead, DataSourceCreate, DataSourceUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.data_source import service
from app.models.data_source import DataSource




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])






@router.get("/", response_model=PaginatedResponse[DataSourceRead])
async def read_datasources(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    type: Optional[str] = Query(None, description="Filter by type"),
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    """
    List DataSource records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        type=type,
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=DataSourceRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_datasource(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    datasource_in: DataSourceCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    try:
        return await service.create(session, datasource_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=DataSourceRead)
async def read_datasource(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    datasource = await service.get(session, id)
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    return datasource

@router.put("/{id}", response_model=DataSourceRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_datasource(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    datasource_in: DataSourceUpdate,
) -> Any:
    
    try:
        datasource = await service.update(session, id, datasource_in)
        return datasource
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_datasource(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    datasource = await service.get(session, id)
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_datasource(
    *,
    session: AsyncSession = Depends(db.get_session),
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple DataSource records by their IDs.
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












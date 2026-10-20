from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps
from app.schemas.data_model import DataModelRead, DataModelCreate, DataModelUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.data_model import service
from app.models.data_model import DataModel




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])






@router.get("/", response_model=PaginatedResponse[DataModelRead])
async def read_datamodels(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    identifier: Optional[str] = Query(None, description="Filter by identifier"),
    
    
    
    
    
    
    
    
    data_source_id: Optional[int] = Query(None, description="Filter by data_source_id"),
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    """
    List DataModel records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        identifier=identifier,
        
        
        
        
        
        
        
        
        data_source_id=data_source_id,
        
    )

@router.post("/", response_model=DataModelRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_datamodel(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    datamodel_in: DataModelCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    try:
        return await service.create(session, datamodel_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=DataModelRead)
async def read_datamodel(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    datamodel = await service.get(session, id)
    if not datamodel:
        raise HTTPException(status_code=404, detail="DataModel not found")
    
    return datamodel

@router.put("/{id}", response_model=DataModelRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_datamodel(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    datamodel_in: DataModelUpdate,
) -> Any:
    
    try:
        datamodel = await service.update(session, id, datamodel_in)
        return datamodel
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_datamodel(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    datamodel = await service.get(session, id)
    if not datamodel:
        raise HTTPException(status_code=404, detail="DataModel not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_datamodel(
    *,
    session: AsyncSession = Depends(db.get_session),
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple DataModel records by their IDs.
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












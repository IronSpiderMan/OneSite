from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.metric import MetricRead, MetricCreate, MetricUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.metric import service
from app.models.metric import Metric





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[MetricRead])
async def read_metrics(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    
    
    recorded_at_from: Optional[datetime] = Query(None, description="Filter by recorded_at from"),
    recorded_at_to: Optional[datetime] = Query(None, description="Filter by recorded_at to"),
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Metric records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        
        
        recorded_at_from=recorded_at_from,
        recorded_at_to=recorded_at_to,
        
        
        
        
        
    )

@router.post("/", response_model=MetricRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_metric(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    metric_in: MetricCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, metric_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=MetricRead)
async def read_metric(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    metric = await service.get(session, id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    return metric

@router.put("/{id}", response_model=MetricRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_metric(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    metric_in: MetricUpdate,
) -> Any:
    
    try:
        metric = await service.update(session, id, metric_in)
        return metric
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_metric(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    metric = await service.get(session, id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_metric(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Metric records by their IDs.
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













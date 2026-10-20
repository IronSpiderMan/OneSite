from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.category import CategoryRead, CategoryCreate, CategoryUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.category import service
from app.models.category import Category





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[CategoryRead])
async def read_categorys(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Category records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        
        
    )

@router.post("/", response_model=CategoryRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_category(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    category_in: CategoryCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, category_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=CategoryRead)
async def read_category(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    category = await service.get(session, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category

@router.put("/{id}", response_model=CategoryRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_category(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    category_in: CategoryUpdate,
) -> Any:
    
    try:
        category = await service.update(session, id, category_in)
        return category
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_category(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    category = await service.get(session, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_category(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Category records by their IDs.
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













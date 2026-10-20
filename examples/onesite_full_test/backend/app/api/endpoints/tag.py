from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.tag import TagRead, TagCreate, TagUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.tag import service
from app.models.tag import Tag




from app.schemas.product import ProductRead




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[TagRead])
async def read_tags(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Tag records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

@router.post("/", response_model=TagRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_tag(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    tag_in: TagCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, tag_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=TagRead)
async def read_tag(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    tag = await service.get(session, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return tag

@router.put("/{id}", response_model=TagRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_tag(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    tag_in: TagUpdate,
) -> Any:
    
    try:
        tag = await service.update(session, id, tag_in)
        return tag
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_tag(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    tag = await service.get(session, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_tag(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Tag records by their IDs.
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









@router.get("/{id}/products", response_model=PaginatedResponse[ProductRead])
async def read_tag_products(
    *,
    session: AsyncSession = Depends(db.get_session),
    id: int,
    page: int = 1,
    size: int = 20,
) -> Any:
    """
    Get Products related to Tag (via M2M)
    """
    return await service.get_products(session, id, page=page, size=size)







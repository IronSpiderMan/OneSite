from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.premium_content import PremiumContentRead, PremiumContentCreate, PremiumContentUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.premium_content import service
from app.models.premium_content import PremiumContent





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])







@router.get("/", response_model=PaginatedResponse[PremiumContentRead])
async def read_premiumcontents(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List PremiumContent records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=PremiumContentRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def create_premiumcontent(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    premiumcontent_in: PremiumContentCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, premiumcontent_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=PremiumContentRead)
async def read_premiumcontent(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    premiumcontent = await service.get(session, id)
    if not premiumcontent:
        raise HTTPException(status_code=404, detail="PremiumContent not found")
    
    return premiumcontent

@router.put("/{id}", response_model=PremiumContentRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_premiumcontent(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    premiumcontent_in: PremiumContentUpdate,
) -> Any:
    
    try:
        premiumcontent = await service.update(session, id, premiumcontent_in)
        return premiumcontent
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def delete_premiumcontent(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    premiumcontent = await service.get(session, id)
    if not premiumcontent:
        raise HTTPException(status_code=404, detail="PremiumContent not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def bulk_delete_premiumcontent(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple PremiumContent records by their IDs.
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













from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.member_only_post import MemberOnlyPostRead, MemberOnlyPostCreate, MemberOnlyPostUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.member_only_post import service
from app.models.member_only_post import MemberOnlyPost





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[MemberOnlyPostRead])
async def read_memberonlyposts(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List MemberOnlyPost records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=MemberOnlyPostRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def create_memberonlypost(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    memberonlypost_in: MemberOnlyPostCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, memberonlypost_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=MemberOnlyPostRead)
async def read_memberonlypost(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    memberonlypost = await service.get(session, id)
    if not memberonlypost:
        raise HTTPException(status_code=404, detail="MemberOnlyPost not found")
    
    return memberonlypost

@router.put("/{id}", response_model=MemberOnlyPostRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_memberonlypost(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    memberonlypost_in: MemberOnlyPostUpdate,
) -> Any:
    
    try:
        memberonlypost = await service.update(session, id, memberonlypost_in)
        return memberonlypost
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))])
async def delete_memberonlypost(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    memberonlypost = await service.get(session, id)
    if not memberonlypost:
        raise HTTPException(status_code=404, detail="MemberOnlyPost not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))])
async def bulk_delete_memberonlypost(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple MemberOnlyPost records by their IDs.
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













from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.user_profile import UserProfileRead, UserProfileCreate, UserProfileUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.user_profile import service
from app.models.user_profile import UserProfile





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[UserProfileRead])
async def read_userprofiles(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    display_name: Optional[str] = Query(None, description="Filter by display_name"),
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List UserProfile records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        display_name=display_name,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=UserProfileRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_userprofile(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    userprofile_in: UserProfileCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, userprofile_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=UserProfileRead)
async def read_userprofile(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    userprofile = await service.get(session, id)
    if not userprofile:
        raise HTTPException(status_code=404, detail="UserProfile not found")
    
    return userprofile

@router.put("/{id}", response_model=UserProfileRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_userprofile(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    userprofile_in: UserProfileUpdate,
) -> Any:
    
    try:
        userprofile = await service.update(session, id, userprofile_in)
        return userprofile
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))])
async def delete_userprofile(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    userprofile = await service.get(session, id)
    if not userprofile:
        raise HTTPException(status_code=404, detail="UserProfile not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.DEVELOPER))])
async def bulk_delete_userprofile(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple UserProfile records by their IDs.
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













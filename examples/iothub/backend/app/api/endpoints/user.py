from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.models.user import User


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps
from app.schemas.user import UserRead, UserCreate, UserUpdate, UserUpdateMe
from app.schemas.pagination import PaginatedResponse
from app.services.user import service
from app.models.user import User




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])






@router.get("/", response_model=PaginatedResponse[UserRead])
async def read_users(
    page: int = 1,
    size: int = 20,
    
    
    
    email: Optional[str] = Query(None, description="Filter by email"),
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
) -> Any:
    
    # User list: only admin and developer
    user_level = deps.ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < deps.ROLE_HIERARCHY.get("admin", 1):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    """
    List User records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        email=email,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=UserRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def create_user(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    user_in: UserCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    if hasattr(user_in, 'role') and user_in.role == 'developer':
        user_level = deps.ROLE_HIERARCHY.get(current_user.role, 0)
        if user_level < deps.ROLE_HIERARCHY.get('developer', 2):
            raise HTTPException(status_code=403, detail="Only developers can create developer accounts")
    
    try:
        return await service.create(session, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserRead)
async def read_me(
    *,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return current_user

@router.put("/me", response_model=UserRead)
async def update_me(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    user_in: UserUpdateMe,
) -> Any:
    try:
        # If changing password, verify old password first
        if user_in.password:
            if not user_in.old_password:
                raise HTTPException(status_code=400, detail="Old password is required to set a new password")
            from app.core.security import verify_password
            if not verify_password(user_in.old_password, current_user.hashed_password):
                raise HTTPException(status_code=400, detail="Old password is incorrect")

        user = await service.update(session, current_user.id, user_in)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/{id}", response_model=UserRead)
async def read_user(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
) -> Any:
    user = await service.get(session, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # User get: only admin and developer (or self)
    if id != current_user.id:
        user_level = deps.ROLE_HIERARCHY.get(current_user.role, 0)
        if user_level < deps.ROLE_HIERARCHY.get("admin", 1):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return user

@router.put("/{id}", response_model=UserRead, dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def update_user(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
    user_in: UserUpdate,
) -> Any:
    
    # User update: admin/developer can update any, user can only update self
    if id != current_user.id:
        user_level = deps.ROLE_HIERARCHY.get(current_user.role, 0)
        if user_level < deps.ROLE_HIERARCHY.get("admin", 1):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    # Admin cannot promote to developer
    if hasattr(user_in, 'role') and user_in.role == 'developer':
        if user_level < deps.ROLE_HIERARCHY.get("developer", 2):
            raise HTTPException(status_code=403, detail="Only developers can promote to developer role")
    
    try:
        user = await service.update(session, id, user_in)
        return user
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def delete_user(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
) -> Any:
    user = await service.get(session, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # User delete: only admin and developer
    user_level = deps.ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < deps.ROLE_HIERARCHY.get("admin", 1):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.ADMIN))])
async def bulk_delete_user(
    *,
    session: AsyncSession = Depends(db.get_session),
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple User records by their IDs.
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












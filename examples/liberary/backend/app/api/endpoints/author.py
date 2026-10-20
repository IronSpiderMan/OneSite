from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.author import AuthorRead, AuthorCreate, AuthorUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.author import service
from app.models.author import Author





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[AuthorRead])
async def read_authors(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Author records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

@router.post("/", response_model=AuthorRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_author(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    author_in: AuthorCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, author_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=AuthorRead)
async def read_author(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    author = await service.get(session, id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    return author

@router.put("/{id}", response_model=AuthorRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_author(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    author_in: AuthorUpdate,
) -> Any:
    
    try:
        author = await service.update(session, id, author_in)
        return author
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_author(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    author = await service.get(session, id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_author(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Author records by their IDs.
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













from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.public_article import PublicArticleRead, PublicArticleCreate, PublicArticleUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.public_article import service
from app.models.public_article import PublicArticle





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[PublicArticleRead])
async def read_publicarticles(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List PublicArticle records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
    )

@router.post("/", response_model=PublicArticleRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_publicarticle(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    publicarticle_in: PublicArticleCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, publicarticle_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=PublicArticleRead)
async def read_publicarticle(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    publicarticle = await service.get(session, id)
    if not publicarticle:
        raise HTTPException(status_code=404, detail="PublicArticle not found")
    
    return publicarticle

@router.put("/{id}", response_model=PublicArticleRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_publicarticle(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    publicarticle_in: PublicArticleUpdate,
) -> Any:
    
    try:
        publicarticle = await service.update(session, id, publicarticle_in)
        return publicarticle
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_publicarticle(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    publicarticle = await service.get(session, id)
    if not publicarticle:
        raise HTTPException(status_code=404, detail="PublicArticle not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_publicarticle(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple PublicArticle records by their IDs.
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













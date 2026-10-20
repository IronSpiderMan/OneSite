from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.subject import SubjectRead, SubjectCreate, SubjectUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.subject import service
from app.models.subject import Subject




from app.schemas.book import BookRead




router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[SubjectRead])
async def read_subjects(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Subject records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
    )

@router.post("/", response_model=SubjectRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_subject(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    subject_in: SubjectCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, subject_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=SubjectRead)
async def read_subject(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    subject = await service.get(session, id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    return subject

@router.put("/{id}", response_model=SubjectRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_subject(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    subject_in: SubjectUpdate,
) -> Any:
    
    try:
        subject = await service.update(session, id, subject_in)
        return subject
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_subject(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    subject = await service.get(session, id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_subject(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Subject records by their IDs.
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









@router.get("/{id}/books", response_model=PaginatedResponse[BookRead])
async def read_subject_books(
    *,
    session: AsyncSession = Depends(db.get_session),
    id: int,
    page: int = 1,
    size: int = 20,
) -> Any:
    """
    Get Books related to Subject (via M2M)
    """
    return await service.get_books(session, id, page=page, size=size)







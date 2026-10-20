from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File

from app.models.user import User


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.book import BookRead, BookCreate, BookUpdate

from app.schemas.pagination import PaginatedResponse
from app.services.book import service
from app.models.book import Book



from app.schemas.subject import SubjectRead





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[BookRead])
async def read_books(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    published_at_from: Optional[datetime] = Query(None, description="Filter by published_at from"),
    published_at_to: Optional[datetime] = Query(None, description="Filter by published_at to"),
    
    
    
    
    
    
    
    
    author_id: Optional[int] = Query(None, description="Filter by author_id"),
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Book records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
        published_at_from=published_at_from,
        published_at_to=published_at_to,
        
        
        
        
        
        
        
        author_id=author_id,
        
        
        
    )

@router.post("/", response_model=BookRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_book(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    book_in: BookCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, book_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=BookRead)
async def read_book(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    book = await service.get(session, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return book

@router.put("/{id}", response_model=BookRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_book(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    book_in: BookUpdate,
) -> Any:
    
    try:
        book = await service.update(session, id, book_in)
        return book
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_book(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    book = await service.get(session, id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_book(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Book records by their IDs.
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





@router.get("/{id}/subjects", response_model=PaginatedResponse[SubjectRead])
async def read_book_subjects(
    *,
    session: AsyncSession = Depends(db.get_session),
    id: int,
    page: int = 1,
    size: int = 20,
) -> Any:
    """
    Get Subjects related to Book
    """
    return await service.get_subjects(session, id, page=page, size=size)












@router.post("/export")
async def export_books(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    filters: Optional[dict] = Body(None),
) -> Any:
    """
    Export Book records to CSV.
    Returns the CSV file directly.
    """
    import os
    import uuid
    from fastapi.responses import FileResponse

    task_id = str(uuid.uuid4())

    # Export synchronously and return file
    filepath = await service.export_to_csv(
        session,
        task_id=task_id,
        user_id=current_user.id,
        filters=filters,
        ws_manager=None,  # No WebSocket progress for synchronous export
    )

    # Return file directly
    filename = os.path.basename(filepath)
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=filename,
    )



@router.post("/import")
async def import_books(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Validate without importing"),
) -> Any:
    """
    Import Book records from CSV.
    Returns the import result directly.
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # Import synchronously and return result
    result = await service.import_from_csv(
        session,
        task_id=task_id,
        user_id=current_user.id,
        file=file,
        dry_run=dry_run,
        ws_manager=None,  # No WebSocket progress for synchronous import
    )
    
    return result




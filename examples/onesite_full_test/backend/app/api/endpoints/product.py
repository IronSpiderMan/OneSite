from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File

from app.models.user import User


from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate, ProductTagMeta

from app.schemas.pagination import PaginatedResponse
from app.services.product import service
from app.models.product import Product



from app.schemas.tag import TagRead





router = APIRouter(dependencies=[Depends(deps.require_role(deps.UserRole.USER))])







@router.get("/", response_model=PaginatedResponse[ProductRead])
async def read_products(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = Query(None, description="Filter by name"),
    
    
    
    
    
    status: Optional[str] = Query(None, description="Filter by status"),
    
    
    
    
    
    is_featured: Optional[bool] = Query(None, description="Filter by is_featured"),
    
    
    
    
    
    
    
    
    
    
    
    created_at_from: Optional[datetime] = Query(None, description="Filter by created_at from"),
    created_at_to: Optional[datetime] = Query(None, description="Filter by created_at to"),
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    category_id: Optional[int] = Query(None, description="Filter by category_id"),
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Product records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
        status=status,
        
        
        
        
        
        is_featured=is_featured,
        
        
        
        
        
        
        
        
        
        
        
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        
        
        
        
        
        
        
        
        
        
        
        
        
        category_id=category_id,
        
        
        
    )

@router.post("/", response_model=ProductRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def create_product(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    product_in: ProductCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, product_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=ProductRead)
async def read_product(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    product = await service.get(session, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

@router.put("/{id}", response_model=ProductRead, dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def update_product(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
    product_in: ProductUpdate,
) -> Any:
    
    try:
        product = await service.update(session, id, product_in)
        return product
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", response_model=dict[str, int], dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def delete_product(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    id: int,
) -> Any:
    product = await service.get(session, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_product(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Product records by their IDs.
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





@router.get("/{id}/tags", response_model=PaginatedResponse[TagRead])
async def read_product_tags(
    *,
    session: AsyncSession = Depends(db.get_session),
    id: int,
    page: int = 1,
    size: int = 20,
) -> Any:
    """
    Get Tags related to Product
    """
    return await service.get_tags(session, id, page=page, size=size)






@router.get("/{id}/tags_with_meta", response_model=PaginatedResponse[ProductTagMeta])
async def read_product_tags_with_meta(
    *,
    session: AsyncSession = Depends(db.get_session),
    id: int,
    page: int = 1,
    size: int = 50,
) -> Any:
    """
    Get Tags related to Product with link-table order
    """
    return await service.get_tags_with_meta(session, id, page=page, size=size)







@router.post("/export")
async def export_products(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    filters: Optional[dict] = Body(None),
) -> Any:
    """
    Export Product records to CSV.
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
async def import_products(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Validate without importing"),
) -> Any:
    """
    Import Product records from CSV.
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




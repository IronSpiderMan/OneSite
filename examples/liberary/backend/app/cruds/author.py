from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.author import Author

from app.schemas.author import AuthorCreate, AuthorUpdate





async def get(session: AsyncSession, id: int) -> Optional[Author]:
    return await session.get(Author, id)



async def check_unique_field(
    session: AsyncSession,
    field_name: str,
    value: Any,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Check if a field value is unique.
    Returns True if unique (no conflict), False if duplicate exists.
    """
    statement = select(Author).where(getattr(Author, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(Author.id != exclude_id)
    result = await session.exec(statement)
    return result.first() is None





def _apply_filters(
    statement,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if name:
        statement = statement.where(col(Author.name).ilike("%" + name + "%"))
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
) -> List[Author]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Author)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

    

    # Apply pagination (skip if size == -1, meaning get all)
    if size != -1:
        skip = (page - 1) * size
        statement = statement.offset(skip).limit(size)

    result = await session.exec(statement)
    return list(result.all())


async def get_multi_with_fk_labels(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
) -> List[Dict[str, Any]]:
    """
    Get list of objects with FK label fields enriched.
    Returns list of dicts with original fields plus {fk_name}_label for each FK.
    """
    # Get base items
    items = await get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

    if not items:
        return []
    
    
    # No FKs, just convert to dicts
    return [item.model_dump() for item in items]
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Author)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: AuthorCreate) -> Author:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Author(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Author, obj_in: AuthorUpdate) -> Author:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Author, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id









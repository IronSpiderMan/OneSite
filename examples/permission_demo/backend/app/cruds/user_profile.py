from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user_profile import UserProfile

from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate





async def get(session: AsyncSession, id: int) -> Optional[UserProfile]:
    return await session.get(UserProfile, id)







def _apply_filters(
    statement,
    *,
    
    
    
    
    
    display_name: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if display_name:
        statement = statement.where(col(UserProfile.display_name).ilike("%" + display_name + "%"))
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    display_name: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
) -> List[UserProfile]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(UserProfile)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        display_name=display_name,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

    
    statement = statement.order_by(col(UserProfile.created_at).desc())
    

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
    
    
    
    
    
    display_name: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
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
        
        
        
        
        
        display_name=display_name,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

    if not items:
        return []
    
    
    # No FKs, just convert to dicts
    return [item.model_dump() for item in items]
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    display_name: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(UserProfile)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        display_name=display_name,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: UserProfileCreate) -> UserProfile:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = UserProfile(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: UserProfile, obj_in: UserProfileUpdate) -> UserProfile:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(UserProfile, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id









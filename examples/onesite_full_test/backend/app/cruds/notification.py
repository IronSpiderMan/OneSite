from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.notification import Notification

from app.schemas.notification import NotificationCreate, NotificationUpdate





async def get(session: AsyncSession, id: int) -> Optional[Notification]:
    return await session.get(Notification, id)







def _apply_filters(
    statement,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    user_id: Optional[int] = None,
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if title:
        statement = statement.where(col(Notification.title).ilike("%" + title + "%"))
    
    
    
    
    
    
    
    
    
    
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    
    
    if user_id is not None:
        if user_id == 0:
            statement = statement.where(Notification.user_id.is_(None))
        else:
            statement = statement.where(Notification.user_id == user_id)
    
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    user_id: Optional[int] = None,
    
    
    
) -> List[Notification]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Notification)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        user_id=user_id,
        
        
        
    )

    
    statement = statement.order_by(col(Notification.created_at).desc())
    

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
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    user_id: Optional[int] = None,
    
    
    
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
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        user_id=user_id,
        
        
        
    )

    if not items:
        return []
    
    
    # Collect unique FK IDs for batch fetch
    
    user_id_ids = list(set(getattr(item, "user_id") for item in items if getattr(item, "user_id") is not None))
    
    
    # Batch fetch FK targets
    
    user_id_map = {}
    if user_id_ids:
        from app.models.user import User
        stmt = select(User).where(User.id.in_(user_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            user_id_map[obj.id] = getattr(obj, "email", None) or str(obj.id)
    
    
    # Enrich items with labels
    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "user_id", None)
        item_dict["user_id_label"] = user_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)
    
    return enriched
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    user_id: Optional[int] = None,
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Notification)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        user_id=user_id,
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: NotificationCreate) -> Notification:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Notification(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Notification, obj_in: NotificationUpdate) -> Notification:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Notification, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id


async def mark_all_read_by_user(session: AsyncSession, user_id: int) -> int:
    """
    Mark all unread notifications as read for a specific user.
    Returns the number of notifications updated.
    """
    from sqlmodel import update

    statement = (
        update(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.is_read == False)
        .values(is_read=True)
    )
    result = await session.exec(statement)
    await session.commit()
    return result.rowcount








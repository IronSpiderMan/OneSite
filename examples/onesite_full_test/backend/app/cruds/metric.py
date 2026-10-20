from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.metric import Metric

from app.schemas.metric import MetricCreate, MetricUpdate





async def get(session: AsyncSession, id: int) -> Optional[Metric]:
    return await session.get(Metric, id)







def _apply_filters(
    statement,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    
    
    recorded_at_from: Optional[datetime] = None,
    recorded_at_to: Optional[datetime] = None,
    
    
    
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if name:
        statement = statement.where(col(Metric.name).ilike("%" + name + "%"))
    
    
    
    
    
    
    
    if recorded_at_from is not None:
        if isinstance(recorded_at_from, datetime) and recorded_at_from.tzinfo is None:
            recorded_at_from = recorded_at_from.replace(tzinfo=timezone.utc)
        statement = statement.where(Metric.recorded_at >= recorded_at_from)
    if recorded_at_to is not None:
        if isinstance(recorded_at_to, datetime) and recorded_at_to.tzinfo is None:
            recorded_at_to = recorded_at_to.replace(tzinfo=timezone.utc)
        statement = statement.where(Metric.recorded_at <= recorded_at_to)
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    
    
    recorded_at_from: Optional[datetime] = None,
    recorded_at_to: Optional[datetime] = None,
    
    
    
    
    
) -> List[Metric]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Metric)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        
        
        recorded_at_from=recorded_at_from,
        recorded_at_to=recorded_at_to,
        
        
        
        
        
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
    
    
    
    
    
    
    
    recorded_at_from: Optional[datetime] = None,
    recorded_at_to: Optional[datetime] = None,
    
    
    
    
    
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
        
        
        
        
        
        
        
        recorded_at_from=recorded_at_from,
        recorded_at_to=recorded_at_to,
        
        
        
        
        
    )

    if not items:
        return []
    
    
    # No FKs, just convert to dicts
    return [item.model_dump() for item in items]
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    
    
    recorded_at_from: Optional[datetime] = None,
    recorded_at_to: Optional[datetime] = None,
    
    
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Metric)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        
        
        recorded_at_from=recorded_at_from,
        recorded_at_to=recorded_at_to,
        
        
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: MetricCreate) -> Metric:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Metric(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Metric, obj_in: MetricUpdate) -> Metric:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Metric, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id









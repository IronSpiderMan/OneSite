from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.data_model import DataModel
from app.schemas.data_model import DataModelCreate, DataModelUpdate



async def get(session: AsyncSession, id: int) -> Optional[DataModel]:
    return await session.get(DataModel, id)



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
    statement = select(DataModel).where(getattr(DataModel, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(DataModel.id != exclude_id)
    result = await session.exec(statement)
    return result.first() is None





def _apply_filters(
    statement,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    identifier: Optional[str] = None,
    
    
    
    
    
    
    
    
    data_source_id: Optional[int] = None,
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if name:
        statement = statement.where(col(DataModel.name).ilike("%" + name + "%"))
    
    
    
    
    
    if identifier:
        statement = statement.where(col(DataModel.identifier).ilike("%" + identifier + "%"))
    
    
    
    
    
    
    

    # Apply foreign key filters
    
    if data_source_id:
        statement = statement.where(DataModel.data_source_id == data_source_id)
    
    
    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    identifier: Optional[str] = None,
    
    
    
    
    
    
    
    
    data_source_id: Optional[int] = None,
    
) -> List[DataModel]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(DataModel)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        identifier=identifier,
        
        
        
        
        
        
        
        
        data_source_id=data_source_id,
        
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
    
    
    
    
    
    identifier: Optional[str] = None,
    
    
    
    
    
    
    
    
    data_source_id: Optional[int] = None,
    
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
        
        
        
        
        
        identifier=identifier,
        
        
        
        
        
        
        
        
        data_source_id=data_source_id,
        
    )
    
    if not items:
        return []
    
    
    # Collect unique FK IDs for batch fetch
    
    data_source_id_ids = list(set(getattr(item, "data_source_id") for item in items if getattr(item, "data_source_id") is not None))
    
    
    # Batch fetch FK targets
    
    data_source_id_map = {}
    if data_source_id_ids:
        from app.models.data_source import DataSource
        stmt = select(DataSource).where(DataSource.id.in_(data_source_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            data_source_id_map[obj.id] = getattr(obj, "name", None) or str(obj.id)
    
    
    # Enrich items with labels
    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "data_source_id", None)
        item_dict["data_source_id_label"] = data_source_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)
    
    return enriched
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    identifier: Optional[str] = None,
    
    
    
    
    
    
    
    
    data_source_id: Optional[int] = None,
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(DataModel)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        identifier=identifier,
        
        
        
        
        
        
        
        
        data_source_id=data_source_id,
        
    )
    
    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: DataModelCreate) -> DataModel:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = DataModel(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: DataModel, obj_in: DataModelUpdate) -> DataModel:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(DataModel, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id








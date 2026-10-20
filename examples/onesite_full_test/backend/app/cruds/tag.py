from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.tag import Tag

from app.schemas.tag import TagCreate, TagUpdate



from app.models.product import Product





async def get(session: AsyncSession, id: int) -> Optional[Tag]:
    return await session.get(Tag, id)



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
    statement = select(Tag).where(getattr(Tag, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(Tag.id != exclude_id)
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
        statement = statement.where(col(Tag.name).ilike("%" + name + "%"))
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
) -> List[Tag]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Tag)
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
    statement = select(func.count()).select_from(Tag)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: TagCreate) -> Tag:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Tag(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Tag, obj_in: TagUpdate) -> Tag:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Tag, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id






# Reverse M2M Relationship CRUD functions

from app.models.product_tag import ProductTag

async def get_products(
    session: AsyncSession,
    tag_id: int,
    page: int = 1,
    size: int = 20,
) -> List[Dict[str, Any]]:
    """Get list of Product objects related to Tag (reverse M2M), enriched with FK labels."""
    # Get source IDs first
    statement = select(ProductTag.product_id).where(
        ProductTag.tag_id == tag_id
    )
    result = await session.exec(statement)
    source_ids = list(result.all())

    if not source_ids:
        return []

    # Pagination
    skip = (page - 1) * size
    paginated_ids = source_ids[skip:skip + size] if size != -1 else source_ids

    # Get objects by IDs
    statement = select(Product).where(
        col(Product.id).in_(paginated_ids)
    )
    result = await session.exec(statement)
    items = list(result.all())

    
    # Import FK target models for label resolution (avoid shadowing Product)
    
    
    from app.models.category import Category
    
    

    # Enrich items with FK labels
    
    category_id_ids = list(set(getattr(item, "category_id") for item in items if getattr(item, "category_id") is not None))
    

    
    category_id_map = {}
    if category_id_ids:
        stmt = select(Category).where(Category.id.in_(category_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            category_id_map[obj.id] = getattr(obj, "name", None) or str(obj.id)
    

    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "category_id", None)
        item_dict["category_id_label"] = category_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)

    return enriched
    


async def count_products(session: AsyncSession, tag_id: int) -> int:
    """Count Products related to Tag (reverse M2M)."""
    statement = select(func.count()).select_from(ProductTag).where(
        ProductTag.tag_id == tag_id
    )
    result = await session.exec(statement)
    return result.one()





from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product

from app.schemas.product import ProductCreate, ProductUpdate


from app.models.product_tag import ProductTag
from app.models.tag import Tag






async def get(session: AsyncSession, id: int) -> Optional[Product]:
    return await session.get(Product, id)





async def get_by_name(
    session: AsyncSession,
    value: Any,
) -> Optional[Product]:
    """
    Get Product by name value.
    Used for import upsert logic.
    """
    statement = select(Product).where(getattr(Product, "name") == value)
    result = await session.exec(statement)
    return result.first()



def _apply_filters(
    statement,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    status: Optional[str] = None,
    
    
    
    
    
    is_featured: Optional[bool] = None,
    
    
    
    
    
    
    
    
    
    
    
    created_at_from: Optional[datetime] = None,
    created_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    category_id: Optional[int] = None,
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if name:
        statement = statement.where(col(Product.name).ilike("%" + name + "%"))
    
    
    
    
    
    if status:
        statement = statement.where(Product.status == status)
    
    
    
    
    
    if is_featured is not None:
        statement = statement.where(Product.is_featured == is_featured)
    
    
    
    
    
    
    
    
    
    
    
    if created_at_from is not None:
        if isinstance(created_at_from, datetime) and created_at_from.tzinfo is None:
            created_at_from = created_at_from.replace(tzinfo=timezone.utc)
        statement = statement.where(Product.created_at >= created_at_from)
    if created_at_to is not None:
        if isinstance(created_at_to, datetime) and created_at_to.tzinfo is None:
            created_at_to = created_at_to.replace(tzinfo=timezone.utc)
        statement = statement.where(Product.created_at <= created_at_to)
    
    
    
    
    
    
    
    
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    
    
    if category_id is not None:
        if category_id == 0:
            statement = statement.where(Product.category_id.is_(None))
        else:
            statement = statement.where(Product.category_id == category_id)
    
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    status: Optional[str] = None,
    
    
    
    
    
    is_featured: Optional[bool] = None,
    
    
    
    
    
    
    
    
    
    
    
    created_at_from: Optional[datetime] = None,
    created_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    category_id: Optional[int] = None,
    
    
    
) -> List[Product]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Product)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        status=status,
        
        
        
        
        
        is_featured=is_featured,
        
        
        
        
        
        
        
        
        
        
        
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        
        
        
        
        
        
        
        
        
        
        
        
        
        category_id=category_id,
        
        
        
    )

    
    statement = statement.order_by(col(Product.created_at).desc())
    

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
    
    
    
    
    
    status: Optional[str] = None,
    
    
    
    
    
    is_featured: Optional[bool] = None,
    
    
    
    
    
    
    
    
    
    
    
    created_at_from: Optional[datetime] = None,
    created_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    category_id: Optional[int] = None,
    
    
    
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
        
        
        
        
        
        status=status,
        
        
        
        
        
        is_featured=is_featured,
        
        
        
        
        
        
        
        
        
        
        
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        
        
        
        
        
        
        
        
        
        
        
        
        
        category_id=category_id,
        
        
        
    )

    if not items:
        return []
    
    
    # Collect unique FK IDs for batch fetch
    
    category_id_ids = list(set(getattr(item, "category_id") for item in items if getattr(item, "category_id") is not None))
    
    
    # Batch fetch FK targets
    
    category_id_map = {}
    if category_id_ids:
        from app.models.category import Category
        stmt = select(Category).where(Category.id.in_(category_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            category_id_map[obj.id] = getattr(obj, "name", None) or str(obj.id)
    
    
    # Enrich items with labels
    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "category_id", None)
        item_dict["category_id_label"] = category_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)
    
    return enriched
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    name: Optional[str] = None,
    
    
    
    
    
    status: Optional[str] = None,
    
    
    
    
    
    is_featured: Optional[bool] = None,
    
    
    
    
    
    
    
    
    
    
    
    created_at_from: Optional[datetime] = None,
    created_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    category_id: Optional[int] = None,
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Product)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        name=name,
        
        
        
        
        
        status=status,
        
        
        
        
        
        is_featured=is_featured,
        
        
        
        
        
        
        
        
        
        
        
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        
        
        
        
        
        
        
        
        
        
        
        
        
        category_id=category_id,
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: ProductCreate) -> Product:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    
    m2m_data = {}
    
    if hasattr(obj_in, "tag_ids"):
        m2m_data["tag_ids"] = getattr(obj_in, "tag_ids")
        delattr(obj_in, "tag_ids")
    
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Product(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    # Insert M2M relations
    
    if m2m_data.get("tag_ids") is not None:
        for idx, target_id in enumerate(m2m_data["tag_ids"], start=1):
            link = ProductTag(
                product_id=db_obj.id,
                tag_id=target_id
                
                , order=idx
                
            )
            session.add(link)
    
    await session.commit()
    await session.refresh(db_obj)
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Product, obj_in: ProductUpdate) -> Product:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    # Handle M2M updates
    
    if "tag_ids" in obj_data:
        new_ids = obj_data.pop("tag_ids")
        if new_ids is not None:
            # 1. Clear existing relations
            # This is a naive implementation (delete all and re-insert). 
            # Better would be to calculate diff.
            statement = select(ProductTag).where(ProductTag.product_id == db_obj.id)
            result = await session.exec(statement)
            existing_links = result.all()
            for link in existing_links:
                await session.delete(link)
            
            # 2. Insert new relations
            for idx, target_id in enumerate(new_ids, start=1):
                link = ProductTag(
                    product_id=db_obj.id,
                    tag_id=target_id
                    
                    , order=idx
                    
                )
                session.add(link)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Product, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id




# M2M Relationship CRUD functions

async def get_tags(
    session: AsyncSession,
    product_id: int,
    page: int = 1,
    size: int = 20,
) -> List[Dict[str, Any]]:
    """Get list of Tag objects related to Product, enriched with FK labels."""
    # Get target IDs first
    statement = select(ProductTag.tag_id).where(
        ProductTag.product_id == product_id
    )
    result = await session.exec(statement)
    target_ids = list(result.all())

    if not target_ids:
        return []

    # Pagination
    skip = (page - 1) * size
    paginated_ids = target_ids[skip:skip + size] if size != -1 else target_ids

    # Get objects by IDs
    statement = select(Tag).where(
        col(Tag.id).in_(paginated_ids)
    )
    result = await session.exec(statement)
    items = list(result.all())

    
    return [item.model_dump() for item in items]
    


async def count_tags(session: AsyncSession, product_id: int) -> int:
    """Count Tags related to Product."""
    statement = select(func.count()).select_from(ProductTag).where(
        ProductTag.product_id == product_id
    )
    result = await session.exec(statement)
    return result.one()


async def get_tags_with_order(
    session: AsyncSession,
    product_id: int,
    page: int = 1,
    size: int = 50,
) -> tuple[List[tuple], int]:
    """Get Tags with order field. Returns (items, total)."""
    skip = (page - 1) * size
    
    # Count total
    total = await count_tags(session, product_id)
    
    if total == 0:
        return [], 0
    
    # Query with join
    from app.models.tag import Tag
    statement = (
        select(Tag.id, Tag.name, ProductTag.order)
        .join(ProductTag, ProductTag.tag_id == Tag.id)
        .where(ProductTag.product_id == product_id)
        .order_by(ProductTag.order)
        .offset(skip)
        .limit(size)
    )
    result = await session.exec(statement)
    rows = result.all()
    
    return rows, total








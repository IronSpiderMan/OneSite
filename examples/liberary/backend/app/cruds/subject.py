from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.subject import Subject

from app.schemas.subject import SubjectCreate, SubjectUpdate



from app.models.book import Book





async def get(session: AsyncSession, id: int) -> Optional[Subject]:
    return await session.get(Subject, id)



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
    statement = select(Subject).where(getattr(Subject, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(Subject.id != exclude_id)
    result = await session.exec(statement)
    return result.first() is None





def _apply_filters(
    statement,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if title:
        statement = statement.where(col(Subject.title).ilike("%" + title + "%"))
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
) -> List[Subject]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Subject)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
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
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
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
        
        
        
        
        
    )

    if not items:
        return []
    
    
    # No FKs, just convert to dicts
    return [item.model_dump() for item in items]
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Subject)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: SubjectCreate) -> Subject:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Subject(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Subject, obj_in: SubjectUpdate) -> Subject:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Subject, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id






# Reverse M2M Relationship CRUD functions

from app.models.book_subject_link import BookSubjectLink

async def get_books(
    session: AsyncSession,
    subject_id: int,
    page: int = 1,
    size: int = 20,
) -> List[Dict[str, Any]]:
    """Get list of Book objects related to Subject (reverse M2M), enriched with FK labels."""
    # Get source IDs first
    statement = select(BookSubjectLink.book_id).where(
        BookSubjectLink.subject_id == subject_id
    )
    result = await session.exec(statement)
    source_ids = list(result.all())

    if not source_ids:
        return []

    # Pagination
    skip = (page - 1) * size
    paginated_ids = source_ids[skip:skip + size] if size != -1 else source_ids

    # Get objects by IDs
    statement = select(Book).where(
        col(Book.id).in_(paginated_ids)
    )
    result = await session.exec(statement)
    items = list(result.all())

    
    # Import FK target models for label resolution (avoid shadowing Book)
    
    
    from app.models.author import Author
    
    

    # Enrich items with FK labels
    
    author_id_ids = list(set(getattr(item, "author_id") for item in items if getattr(item, "author_id") is not None))
    

    
    author_id_map = {}
    if author_id_ids:
        stmt = select(Author).where(Author.id.in_(author_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            author_id_map[obj.id] = getattr(obj, "name", None) or str(obj.id)
    

    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "author_id", None)
        item_dict["author_id_label"] = author_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)

    return enriched
    


async def count_books(session: AsyncSession, subject_id: int) -> int:
    """Count Books related to Subject (reverse M2M)."""
    statement = select(func.count()).select_from(BookSubjectLink).where(
        BookSubjectLink.subject_id == subject_id
    )
    result = await session.exec(statement)
    return result.one()





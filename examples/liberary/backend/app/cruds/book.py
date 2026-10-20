from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.book import Book

from app.schemas.book import BookCreate, BookUpdate


from app.models.book_subject_link import BookSubjectLink
from app.models.subject import Subject






async def get(session: AsyncSession, id: int) -> Optional[Book]:
    return await session.get(Book, id)



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
    statement = select(Book).where(getattr(Book, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(Book.id != exclude_id)
    result = await session.exec(statement)
    return result.first() is None



async def get_by_title(
    session: AsyncSession,
    value: Any,
) -> Optional[Book]:
    """
    Get Book by title value.
    Used for import upsert logic.
    """
    statement = select(Book).where(getattr(Book, "title") == value)
    result = await session.exec(statement)
    return result.first()



def _apply_filters(
    statement,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    published_at_from: Optional[datetime] = None,
    published_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    
    author_id: Optional[int] = None,
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    
    
    if title:
        statement = statement.where(col(Book.title).ilike("%" + title + "%"))
    
    
    
    
    
    if published_at_from is not None:
        if isinstance(published_at_from, datetime) and published_at_from.tzinfo is None:
            published_at_from = published_at_from.replace(tzinfo=timezone.utc)
        statement = statement.where(Book.published_at >= published_at_from)
    if published_at_to is not None:
        if isinstance(published_at_to, datetime) and published_at_to.tzinfo is None:
            published_at_to = published_at_to.replace(tzinfo=timezone.utc)
        statement = statement.where(Book.published_at <= published_at_to)
    
    
    
    
    

    # Apply foreign key filters (0 = sentinel for IS NULL)
    
    
    if author_id is not None:
        if author_id == 0:
            statement = statement.where(Book.author_id.is_(None))
        else:
            statement = statement.where(Book.author_id == author_id)
    
    

    

    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    published_at_from: Optional[datetime] = None,
    published_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    author_id: Optional[int] = None,
    
    
    
) -> List[Book]:
    """
    Get list of objects with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of objects; use count() for total.
    """
    statement = select(Book)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
        published_at_from=published_at_from,
        published_at_to=published_at_to,
        
        
        
        
        
        
        
        author_id=author_id,
        
        
        
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
    
    
    
    
    
    published_at_from: Optional[datetime] = None,
    published_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    author_id: Optional[int] = None,
    
    
    
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
        
        
        
        
        
        published_at_from=published_at_from,
        published_at_to=published_at_to,
        
        
        
        
        
        
        
        author_id=author_id,
        
        
        
    )

    if not items:
        return []
    
    
    # Collect unique FK IDs for batch fetch
    
    author_id_ids = list(set(getattr(item, "author_id") for item in items if getattr(item, "author_id") is not None))
    
    
    # Batch fetch FK targets
    
    author_id_map = {}
    if author_id_ids:
        from app.models.author import Author
        stmt = select(Author).where(Author.id.in_(author_id_ids))
        result = await session.exec(stmt)
        for obj in result.all():
            author_id_map[obj.id] = getattr(obj, "name", None) or str(obj.id)
    
    
    # Enrich items with labels
    enriched = []
    for item in items:
        item_dict = item.model_dump()
        
        fk_id = getattr(item, "author_id", None)
        item_dict["author_id_label"] = author_id_map.get(fk_id) if fk_id else None
        
        enriched.append(item_dict)
    
    return enriched
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    
    
    title: Optional[str] = None,
    
    
    
    
    
    published_at_from: Optional[datetime] = None,
    published_at_to: Optional[datetime] = None,
    
    
    
    
    
    
    
    author_id: Optional[int] = None,
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(Book)
    statement = _apply_filters(
        statement,
        
        
        
        
        
        title=title,
        
        
        
        
        
        published_at_from=published_at_from,
        published_at_to=published_at_to,
        
        
        
        
        
        
        
        author_id=author_id,
        
        
        
    )

    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: BookCreate) -> Book:
    # Note: validation should happen before, here we assume obj_in is valid pydantic model
    
    # Handle M2M fields
    
    m2m_data = {}
    
    if hasattr(obj_in, "subject_ids"):
        m2m_data["subject_ids"] = getattr(obj_in, "subject_ids")
        delattr(obj_in, "subject_ids")
    
    

    # Convert to dict to handle nested Pydantic models in JSON fields
    obj_dict = obj_in.dict()
    db_obj = Book(**obj_dict)
    
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    
    
    # Insert M2M relations
    
    if m2m_data.get("subject_ids") is not None:
        for idx, target_id in enumerate(m2m_data["subject_ids"], start=1):
            link = BookSubjectLink(
                book_id=db_obj.id,
                subject_id=target_id
                
            )
            session.add(link)
    
    await session.commit()
    await session.refresh(db_obj)
    
    
    return db_obj

async def update(session: AsyncSession, db_obj: Book, obj_in: BookUpdate) -> Book:
    obj_data = obj_in.dict(exclude_unset=True)
    
    
    # Handle M2M updates
    
    if "subject_ids" in obj_data:
        new_ids = obj_data.pop("subject_ids")
        if new_ids is not None:
            # 1. Clear existing relations
            # This is a naive implementation (delete all and re-insert). 
            # Better would be to calculate diff.
            statement = select(BookSubjectLink).where(BookSubjectLink.book_id == db_obj.id)
            result = await session.exec(statement)
            existing_links = result.all()
            for link in existing_links:
                await session.delete(link)
            
            # 2. Insert new relations
            for idx, target_id in enumerate(new_ids, start=1):
                link = BookSubjectLink(
                    book_id=db_obj.id,
                    subject_id=target_id
                    
                )
                session.add(link)
    
    
    
    for key, value in obj_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> int:
    db_obj = await session.get(Book, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj.id




# M2M Relationship CRUD functions

async def get_subjects(
    session: AsyncSession,
    book_id: int,
    page: int = 1,
    size: int = 20,
) -> List[Dict[str, Any]]:
    """Get list of Subject objects related to Book, enriched with FK labels."""
    # Get target IDs first
    statement = select(BookSubjectLink.subject_id).where(
        BookSubjectLink.book_id == book_id
    )
    result = await session.exec(statement)
    target_ids = list(result.all())

    if not target_ids:
        return []

    # Pagination
    skip = (page - 1) * size
    paginated_ids = target_ids[skip:skip + size] if size != -1 else target_ids

    # Get objects by IDs
    statement = select(Subject).where(
        col(Subject.id).in_(paginated_ids)
    )
    result = await session.exec(statement)
    items = list(result.all())

    
    return [item.model_dump() for item in items]
    


async def count_subjects(session: AsyncSession, book_id: int) -> int:
    """Count Subjects related to Book."""
    statement = select(func.count()).select_from(BookSubjectLink).where(
        BookSubjectLink.book_id == book_id
    )
    result = await session.exec(statement)
    return result.one()









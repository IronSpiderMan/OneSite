from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserUpdateMe


async def get(session: AsyncSession, id: int) -> Optional[User]:
    return await session.get(User, id)



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
    statement = select(User).where(getattr(User, field_name) == value)
    if exclude_id is not None:
        statement = statement.where(User.id != exclude_id)
    result = await session.exec(statement)
    return result.first() is None



def _apply_filters(
    statement,
    *,
    
    
    
    email: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
):
    """Apply search and filter conditions to statement. Shared by get_multi and count."""
    # Apply per-field filters (configured via site_props.is_search_field)
    
    
    
    if email:
        statement = statement.where(col(User.email).ilike("%" + email + "%"))
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    # Apply foreign key filters
    
    
    return statement


async def get_multi(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    
    
    
    email: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
) -> List[User]:
    """
    Get list of users with optional search and filter support.
    When size=-1, returns all matching records without pagination.
    Returns only the list of users; use count() for total.
    """
    statement = select(User)
    statement = _apply_filters(
        statement,
        
        
        
        email=email,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )

    
    statement = statement.order_by(col(User.created_at).desc())
    

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
    
    
    
    email: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
) -> List[Dict[str, Any]]:
    """
    Get list of users with FK label fields enriched.
    Returns list of dicts with original fields plus {fk_name}_label for each FK.
    """
    # Get base items
    items = await get_multi(
        session,
        page=page,
        size=size,
        
        
        
        email=email,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )
    
    if not items:
        return []
    
    
    # No FKs, just convert to dicts
    return [item.model_dump() for item in items]
    


async def count(
    session: AsyncSession,
    *,
    
    
    
    email: Optional[str] = None,
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
) -> int:
    """
    Count total matching records with same filter conditions as get_multi.
    """
    statement = select(func.count()).select_from(User)
    statement = _apply_filters(
        statement,
        
        
        
        email=email,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    )
    
    result = await session.exec(statement)
    return result.one()

async def create(session: AsyncSession, obj_in: UserCreate) -> User:
    # User creation logic is mainly handled in Service (password hashing)
    
    db_obj = User.from_orm(obj_in)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def update(session: AsyncSession, db_obj: User, obj_in: Union[UserUpdate, UserUpdateMe]) -> User:
    hero_data = obj_in.dict(exclude_unset=True)
    # Remove password from data if present (it's transient)
    if 'password' in hero_data:
        del hero_data['password']
    if 'old_password' in hero_data:
        del hero_data['old_password']

    for key, value in hero_data.items():
        setattr(db_obj, key, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete(session: AsyncSession, id: int) -> User:
    db_obj = await session.get(User, id)
    await session.delete(db_obj)
    await session.commit()
    return db_obj



from typing import Optional, Union
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from app.cruds import user as crud
from app.schemas.user import UserCreate, UserUpdate, UserUpdateMe
from app.schemas.pagination import PaginatedResponse
from app.models.user import User


class UserService:
    async def get(self, session: AsyncSession, id: int) -> Optional[User]:
        return await crud.get(session, id)

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        email: Optional[str] = None,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    ) -> PaginatedResponse[User]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            email=email,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
        )
        
        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            email=email,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
        )
        
        # Build response
        if size == -1:
            return PaginatedResponse.create(data=items, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: UserCreate) -> User:
        
        # Check unique field constraints
        
        
        if getattr(obj_in, "email", None) is not None:
            if not await crud.check_unique_field(session, "email", obj_in.email):
                raise ValueError("email already exists")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        from app.core.security import get_password_hash
        user_data = obj_in.dict()
        if 'password' in user_data:
            password = user_data.pop('password')
            user_data['hashed_password'] = get_password_hash(password)
        db_obj = User(**user_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def update(self, session: AsyncSession, id: int, obj_in: Union[UserUpdate, UserUpdateMe]) -> User:
        """
        Update User by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("User not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        if getattr(obj_in, "email", None) is not None and getattr(obj_in, "email") != getattr(db_obj, "email"):
            if not await crud.check_unique_field(session, "email", obj_in.email, exclude_id=id):
                raise ValueError("email already exists")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        if hasattr(obj_in, 'password') and obj_in.password:
            from app.core.security import get_password_hash
            db_obj.hashed_password = get_password_hash(obj_in.password)
        
        return await crud.update(session, db_obj, obj_in)

    async def delete(self, session: AsyncSession, id: int) -> User:
        return await crud.delete(session, id)

    

service = UserService()
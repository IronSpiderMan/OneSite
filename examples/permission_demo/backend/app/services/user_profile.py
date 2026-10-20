import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user_profile import UserProfile
from app.cruds import user_profile as crud
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.user_profile import UserProfileRead




logger = logging.getLogger(__name__)

class UserProfileService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[UserProfileRead]:
        obj = await crud.get(session, id)
        return UserProfileRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        display_name: Optional[str] = None,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    ) -> PaginatedResponse[UserProfileRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            display_name=display_name,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            display_name=display_name,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
        )

        # Build response
        items_read = [UserProfileRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: UserProfileCreate) -> UserProfileRead:
        
        
        obj = await crud.create(session, obj_in)

        

        
        return UserProfileRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: UserProfileUpdate) -> UserProfileRead:
        """
        Update UserProfile by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("UserProfile not found")
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return UserProfileRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    


service = UserProfileService()
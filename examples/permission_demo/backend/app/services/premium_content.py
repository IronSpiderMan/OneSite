import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.premium_content import PremiumContent
from app.cruds import premium_content as crud
from app.schemas.premium_content import PremiumContentCreate, PremiumContentUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.premium_content import PremiumContentRead




logger = logging.getLogger(__name__)

class PremiumContentService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[PremiumContentRead]:
        obj = await crud.get(session, id)
        return PremiumContentRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        title: Optional[str] = None,
        
        
        
        
        
        
        
        
        
        
        
        
    ) -> PaginatedResponse[PremiumContentRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            title=title,
            
            
            
            
            
            
            
            
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            title=title,
            
            
            
            
            
            
            
            
            
            
            
        )

        # Build response
        items_read = [PremiumContentRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: PremiumContentCreate) -> PremiumContentRead:
        
        
        obj = await crud.create(session, obj_in)

        

        
        return PremiumContentRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: PremiumContentUpdate) -> PremiumContentRead:
        """
        Update PremiumContent by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("PremiumContent not found")
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return PremiumContentRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    


service = PremiumContentService()
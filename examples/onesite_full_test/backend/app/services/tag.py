import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.tag import Tag
from app.cruds import tag as crud
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.tag import TagRead



from app.schemas.product import ProductRead




logger = logging.getLogger(__name__)

class TagService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[TagRead]:
        obj = await crud.get(session, id)
        return TagRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        
    ) -> PaginatedResponse[TagRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            name=name,
            
            
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            name=name,
            
            
            
            
            
        )

        # Build response
        items_read = [TagRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: TagCreate) -> TagRead:
        
        # Check unique field constraints
        
        
        
        
        if getattr(obj_in, "name", None) is not None:
            if not await crud.check_unique_field(session, "name", obj_in.name):
                raise ValueError("name already exists")
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return TagRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: TagUpdate) -> TagRead:
        """
        Update Tag by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Tag not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        if getattr(obj_in, "name", None) is not None and getattr(obj_in, "name") != getattr(db_obj, "name"):
            if not await crud.check_unique_field(session, "name", obj_in.name, exclude_id=id):
                raise ValueError("name already exists")
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return TagRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    
    # Reverse M2M Relationship methods
    
    async def get_products(
        self,
        session: AsyncSession,
        tag_id: int,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[ProductRead]:
        """
        Get Products related to Tag (via M2M).
        """
        # Get total count
        total = await crud.count_products(session, tag_id)

        if total == 0:
            return PaginatedResponse.create(data=[], total=0, page=page, size=size)

        # Get items (CRUD returns objects directly with pagination)
        items = await crud.get_products(session, tag_id, page=page, size=size)

        # Convert to ReadSchema
        items_read = [ProductRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)
    
    

    

    

    


service = TagService()
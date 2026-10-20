import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.subject import Subject
from app.cruds import subject as crud
from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.subject import SubjectRead



from app.schemas.book import BookRead




logger = logging.getLogger(__name__)

class SubjectService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[SubjectRead]:
        obj = await crud.get(session, id)
        return SubjectRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        title: Optional[str] = None,
        
        
        
        
        
        
    ) -> PaginatedResponse[SubjectRead]:
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
        items_read = [SubjectRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: SubjectCreate) -> SubjectRead:
        
        # Check unique field constraints
        
        
        
        
        if getattr(obj_in, "title", None) is not None:
            if not await crud.check_unique_field(session, "title", obj_in.title):
                raise ValueError("title already exists")
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return SubjectRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: SubjectUpdate) -> SubjectRead:
        """
        Update Subject by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Subject not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        if getattr(obj_in, "title", None) is not None and getattr(obj_in, "title") != getattr(db_obj, "title"):
            if not await crud.check_unique_field(session, "title", obj_in.title, exclude_id=id):
                raise ValueError("title already exists")
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return SubjectRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    
    # Reverse M2M Relationship methods
    
    async def get_books(
        self,
        session: AsyncSession,
        subject_id: int,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BookRead]:
        """
        Get Books related to Subject (via M2M).
        """
        # Get total count
        total = await crud.count_books(session, subject_id)

        if total == 0:
            return PaginatedResponse.create(data=[], total=0, page=page, size=size)

        # Get items (CRUD returns objects directly with pagination)
        items = await crud.get_books(session, subject_id, page=page, size=size)

        # Convert to ReadSchema
        items_read = [BookRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)
    
    

    

    

    


service = SubjectService()
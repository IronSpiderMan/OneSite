import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.author import Author
from app.cruds import author as crud
from app.schemas.author import AuthorCreate, AuthorUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.author import AuthorRead




logger = logging.getLogger(__name__)

class AuthorService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[AuthorRead]:
        obj = await crud.get(session, id)
        return AuthorRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        
    ) -> PaginatedResponse[AuthorRead]:
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
        items_read = [AuthorRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: AuthorCreate) -> AuthorRead:
        
        # Check unique field constraints
        
        
        
        
        if getattr(obj_in, "name", None) is not None:
            if not await crud.check_unique_field(session, "name", obj_in.name):
                raise ValueError("name already exists")
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return AuthorRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: AuthorUpdate) -> AuthorRead:
        """
        Update Author by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Author not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        if getattr(obj_in, "name", None) is not None and getattr(obj_in, "name") != getattr(db_obj, "name"):
            if not await crud.check_unique_field(session, "name", obj_in.name, exclude_id=id):
                raise ValueError("name already exists")
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return AuthorRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    


service = AuthorService()
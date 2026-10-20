import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.data_model import DataModel
from app.cruds import data_model as crud
from app.schemas.data_model import DataModelCreate, DataModelUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.data_model import DataModelRead




logger = logging.getLogger(__name__)

class DataModelService:
    async def get(self, session: AsyncSession, id: int) -> Optional[DataModelRead]:
        obj = await crud.get(session, id)
        return DataModelRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        identifier: Optional[str] = None,
        
        
        
        
        
        
        
        
        data_source_id: Optional[int] = None,
        
    ) -> PaginatedResponse[DataModelRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            name=name,
            
            
            
            
            
            identifier=identifier,
            
            
            
            
            
            
            
            
            data_source_id=data_source_id,
            
        )
        
        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            name=name,
            
            
            
            
            
            identifier=identifier,
            
            
            
            
            
            
            
            
            data_source_id=data_source_id,
            
        )
        
        # Build response
        items_read = [DataModelRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: DataModelCreate) -> DataModelRead:
        
        # Check unique field constraints
        
        
        
        
        
        
        if getattr(obj_in, "identifier", None) is not None:
            if not await crud.check_unique_field(session, "identifier", obj_in.identifier):
                raise ValueError("identifier already exists")
        
        
        
        
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return DataModelRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: DataModelUpdate) -> DataModelRead:
        """
        Update DataModel by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("DataModel not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        
        
        if getattr(obj_in, "identifier", None) is not None and getattr(obj_in, "identifier") != getattr(db_obj, "identifier"):
            if not await crud.check_unique_field(session, "identifier", obj_in.identifier, exclude_id=id):
                raise ValueError("identifier already exists")
        
        
        
        
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return DataModelRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    

service = DataModelService()
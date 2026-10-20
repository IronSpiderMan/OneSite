import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.metric import Metric
from app.cruds import metric as crud
from app.schemas.metric import MetricCreate, MetricUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.metric import MetricRead




logger = logging.getLogger(__name__)

class MetricService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[MetricRead]:
        obj = await crud.get(session, id)
        return MetricRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        
        
        recorded_at_from: Optional[datetime] = None,
        recorded_at_to: Optional[datetime] = None,
        
        
        
        
        
        
    ) -> PaginatedResponse[MetricRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            name=name,
            
            
            
            
            
            
            
            recorded_at_from=recorded_at_from,
            recorded_at_to=recorded_at_to,
            
            
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            name=name,
            
            
            
            
            
            
            
            recorded_at_from=recorded_at_from,
            recorded_at_to=recorded_at_to,
            
            
            
            
            
        )

        # Build response
        items_read = [MetricRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: MetricCreate) -> MetricRead:
        
        
        obj = await crud.create(session, obj_in)

        

        
        return MetricRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: MetricUpdate) -> MetricRead:
        """
        Update Metric by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Metric not found")
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return MetricRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    


service = MetricService()
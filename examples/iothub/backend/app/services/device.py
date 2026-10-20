import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.device import Device
from app.cruds import device as crud
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.device import DeviceRead




logger = logging.getLogger(__name__)

class DeviceService:
    async def get(self, session: AsyncSession, id: int) -> Optional[DeviceRead]:
        obj = await crud.get(session, id)
        return DeviceRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        device_key: Optional[str] = None,
        
        
        
        
        
        status: Optional[str] = None,
        
        
        
        
        
        
        data_model_id: Optional[int] = None,
        
    ) -> PaginatedResponse[DeviceRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            name=name,
            
            
            
            
            
            device_key=device_key,
            
            
            
            
            
            status=status,
            
            
            
            
            
            
            data_model_id=data_model_id,
            
        )
        
        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            name=name,
            
            
            
            
            
            device_key=device_key,
            
            
            
            
            
            status=status,
            
            
            
            
            
            
            data_model_id=data_model_id,
            
        )
        
        # Build response
        items_read = [DeviceRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: DeviceCreate) -> DeviceRead:
        
        # Check unique field constraints
        
        
        
        
        
        
        if getattr(obj_in, "device_key", None) is not None:
            if not await crud.check_unique_field(session, "device_key", obj_in.device_key):
                raise ValueError("device_key already exists")
        
        
        
        
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return DeviceRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: DeviceUpdate) -> DeviceRead:
        """
        Update Device by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Device not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        
        
        if getattr(obj_in, "device_key", None) is not None and getattr(obj_in, "device_key") != getattr(db_obj, "device_key"):
            if not await crud.check_unique_field(session, "device_key", obj_in.device_key, exclude_id=id):
                raise ValueError("device_key already exists")
        
        
        
        
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return DeviceRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    

    

    

    

    

service = DeviceService()
import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.notification import Notification
from app.cruds import notification as crud
from app.schemas.notification import NotificationCreate, NotificationUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.notification import NotificationRead



from app.core.ws import manager


logger = logging.getLogger(__name__)

class NotificationService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[NotificationRead]:
        obj = await crud.get(session, id)
        return NotificationRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        title: Optional[str] = None,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        user_id: Optional[int] = None,
        
        
        
    ) -> PaginatedResponse[NotificationRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            title=title,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            user_id=user_id,
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            title=title,
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            user_id=user_id,
            
            
            
        )

        # Build response
        items_read = [NotificationRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: NotificationCreate) -> NotificationRead:
        
        
        # If user_id is None, broadcast to all active users
        if getattr(obj_in, "user_id", None) is None:
            from sqlmodel import select
            from app.models.user import User
            
            result = await session.exec(select(User.id).where(User.is_active == True))
            user_ids = result.all()
            
            if not user_ids:
                # No active users, return placeholder
                return NotificationRead.model_validate(Notification(
                    title=obj_in.title,
                    summary=obj_in.summary,
                    content=obj_in.content,
                    is_read=False,
                    user_id=0
                ))
            
            created_at = datetime.now(timezone.utc)
            created_objects = []
            
            for uid in user_ids:
                obj_data = obj_in.dict()
                obj_data["user_id"] = uid
                obj_data["created_at"] = created_at
                db_obj = Notification(**obj_data)
                session.add(db_obj)
                created_objects.append(db_obj)
            
            await session.commit()
            
            # Refresh all objects to get their IDs
            for obj in created_objects:
                await session.refresh(obj)
            
            # Push notifications to all users
            for obj in created_objects:
                try:
                    payload = {
                        "type": "notification",
                        "data": {
                            "id": obj.id,
                            "title": obj.title,
                            "summary": obj.summary,
                            "created_at": obj.created_at.isoformat() if obj.created_at else None,
                            "is_read": obj.is_read,
                        }
                    }
                    await manager.send_personal_message(payload, obj.user_id)
                except Exception as e:
                    logger.exception("Failed to push notification via WebSocket: %s", e)
            
            # Return the first created object as representative
            return NotificationRead.model_validate(created_objects[0]) if created_objects else NotificationRead.model_validate(Notification())
        
        obj = await crud.create(session, obj_in)

        

        
        # Auto-push for notification
        try:
            created_at = getattr(obj, "created_at", None)
            payload = {
                "type": "notification",
                "data": {
                    "id": getattr(obj, "id", None),
                    "title": getattr(obj, "title", ""),
                    "summary": getattr(obj, "summary", ""),
                    "created_at": created_at.isoformat() if created_at else None,
                    "is_read": bool(getattr(obj, "is_read", False)),
                }
            }
            await manager.send_personal_message(payload, obj.user_id)
        except Exception as e:
            logger.exception("Failed to send notification push via WebSocket: %s", e)
        
        return NotificationRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: NotificationUpdate) -> NotificationRead:
        """
        Update Notification by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Notification not found")
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        # Auto-push read status
        try:
            if getattr(obj, "is_read", False):
                await manager.send_personal_message({"type": "read", "id": obj.id}, obj.user_id)
        except Exception as e:
            logger.exception("Failed to send read status via WebSocket: %s", e)
        
        return NotificationRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    
    async def mark_all_read(self, session: AsyncSession, user_id: int) -> int:
        """
        Mark all unread notifications as read for a specific user.
        Returns the number of notifications updated.
        """
        updated_count = await crud.mark_all_read_by_user(session, user_id)
        
        # Push read status for all to WebSocket
        try:
            # Push a single "all_read" event to notify the frontend to refresh
            await manager.send_personal_message({"type": "all_read", "user_id": user_id}, user_id)
        except Exception as e:
            logger.exception("Failed to send all_read event via WebSocket: %s", e)
        
        return updated_count
    

    

    

    

    

    


service = NotificationService()
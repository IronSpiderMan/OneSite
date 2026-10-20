from typing import List, Any, Optional, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.models.user import User


from sqlmodel import select, func, col

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core import db, deps

from app.schemas.notification import NotificationRead, NotificationCreate, NotificationUpdate, NotificationSend

from app.schemas.pagination import PaginatedResponse
from app.services.notification import service
from app.models.notification import Notification





router = APIRouter()



@router.get("/unread_count")
async def unread_count(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    statement = select(func.count()).select_from(Notification).where(
        col(Notification.user_id) == current_user.id,
        col(Notification.is_read) == False,
    )
    result = await session.exec(statement)
    return {"unread": result.one()}

@router.get("/inbox", response_model=PaginatedResponse[NotificationRead])
async def inbox(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    page: int = 1,
    size: int = 20,
) -> Any:
    skip = (page - 1) * size
    statement = (
        select(Notification)
        .where(col(Notification.user_id) == current_user.id)
        .order_by(col(Notification.created_at).desc())
    )
    total_statement = select(func.count()).select_from(statement.subquery())
    total_result = await session.exec(total_statement)
    total = total_result.one()
    result = await session.exec(statement.offset(skip).limit(size))
    items = result.all()
    return PaginatedResponse.create(data=items, total=total, page=page, size=size)

@router.put("/{id}/read", response_model=NotificationRead)
async def mark_read(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
    id: int,
) -> Any:
    n = await service.get(session, id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if getattr(n, "user_id", None) != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not getattr(n, "is_read", False):
        n = await service.update(session, id, NotificationUpdate(is_read=True))
    return n

@router.put("/mark_all_read")
async def mark_all_read(
    *,
    session: AsyncSession = Depends(db.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Mark all unread notifications as read for the current user.
    Returns the count of notifications marked as read.
    """
    updated_count = await service.mark_all_read(session, current_user.id)
    return {"updated": updated_count}

@router.post("/send", dependencies=[Depends(deps.get_current_active_superuser)])
async def send_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    payload: NotificationSend,
) -> Any:
    title = str(payload.title or "").strip()
    content = str(payload.content or "").strip()
    summary = str(payload.summary or "").strip()
    user_id = payload.user_id
    broadcast = bool(payload.broadcast)
    if not title or not content:
        raise HTTPException(status_code=400, detail="title/content required")

    # Determine broadcast mode: explicit broadcast=True OR user_id is None
    is_broadcast = broadcast or (user_id is None)
    
    created_count = 0
    if is_broadcast:
        q = await session.exec(select(User.id).where(User.is_active == True))
        user_ids = q.all()
        for uid in user_ids:
            obj_in = NotificationCreate(title=title, summary=summary or title, content=content, user_id=uid, is_read=False)
            await service.create(session, obj_in)
            created_count += 1
    else:
        try:
            uid = int(user_id)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid user_id")
        obj_in = NotificationCreate(title=title, summary=summary or title, content=content, user_id=uid, is_read=False)
        await service.create(session, obj_in)
        created_count = 1
    return {"sent": created_count}





@router.get("/", response_model=PaginatedResponse[NotificationRead], dependencies=[Depends(deps.get_current_user)])
async def read_notifications(
    page: int = 1,
    size: int = 20,
    
    
    
    
    
    title: Optional[str] = Query(None, description="Filter by title"),
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    user_id: Optional[int] = Query(None, description="Filter by user_id"),
    
    
    session: AsyncSession = Depends(db.get_session),
    
) -> Any:
    
    
    """
    List Notification records with optional search and filter support.
    """
    return await service.get_multi(
        session,
        page=page,
        size=size,
        
        
        
        
        
        title=title,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        user_id=user_id,
        
        
        
    )

@router.post("/", response_model=NotificationRead, dependencies=[Depends(deps.get_current_user)])
async def create_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    notification_in: NotificationCreate,
) -> Any:
    # Special permission check: admin cannot create developer role
    
    
    try:
        return await service.create(session, notification_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.get("/{id}", response_model=NotificationRead, dependencies=[Depends(deps.get_current_user)])
async def read_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
) -> Any:
    notification = await service.get(session, id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if getattr(notification, "user_id", None) != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return notification

@router.put("/{id}", response_model=NotificationRead, dependencies=[Depends(deps.get_current_user)])
async def update_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
    notification_in: NotificationUpdate,
) -> Any:
    
    # Check permission for notification
    notification = await service.get(session, id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if getattr(notification, "user_id", None) != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        notification = await service.update(session, id, notification_in)
        return notification
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", dependencies=[Depends(deps.get_current_user)])
async def delete_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    current_user: User = Depends(deps.get_current_user),
    
    id: int,
) -> Any:
    notification = await service.get(session, id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if getattr(notification, "user_id", None) != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        deleted = await service.delete(session, id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete: related records still exist")
    return {"deleted": deleted}

@router.post("/bulk_delete", dependencies=[Depends(deps.require_role(deps.UserRole.USER))])
async def bulk_delete_notification(
    *,
    session: AsyncSession = Depends(db.get_session),
    
    ids: Annotated[List[int], Body(embed=True)],
) -> Any:
    """
    Delete multiple Notification records by their IDs.
    """
    
    deleted_count = 0
    for id in ids:
        obj = await service.get(session, id)
        if obj:
            
            try:
                await service.delete(session, id)
                deleted_count += 1
            except IntegrityError:
                await session.rollback()
                raise HTTPException(status_code=400, detail="Cannot delete: some records have related data that prevents deletion")
    return {"deleted": deleted_count}













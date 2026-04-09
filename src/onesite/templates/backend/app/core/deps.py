from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import config, db
from app.models.user import User, UserRole
from app.core.config import settings

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

# Role hierarchy: higher index = more privileges
ROLE_HIERARCHY = {
    UserRole.USER: 0,
    UserRole.ADMIN: 1,
    UserRole.DEVELOPER: 2,
}

async def get_current_user(
    session: AsyncSession = Depends(db.get_session),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        # In a real app, define TokenPayload schema
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=403, detail="Could not validate credentials")
    except (JWTError, ValidationError):
        raise HTTPException(status_code=403, detail="Could not validate credentials")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def require_role(min_role: UserRole):
    """Dependency factory that requires user to have at least min_role."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=403, detail="The user doesn't have enough privileges"
            )
        return current_user
    return checker

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    # Superuser = admin or developer (role >= ADMIN)
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < ROLE_HIERARCHY.get(UserRole.ADMIN, 0):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < ROLE_HIERARCHY.get(UserRole.ADMIN, 0):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_current_active_developer(
    current_user: User = Depends(get_current_user),
) -> User:
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < ROLE_HIERARCHY.get(UserRole.DEVELOPER, 0):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.db import get_session
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, UserRegister
from app.services.system_config import service as system_config_service
from app.services.user import service as user_service

async def public_actor():
    from types import SimpleNamespace
    from app.core.access import current_actor
    token = current_actor.set(SimpleNamespace(role="user", id=None))
    try:
        yield
    finally:
        current_actor.reset(token)


router = APIRouter(dependencies=[Depends(public_actor)])


@router.get("/public-config")
async def public_config(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Branding and registration settings needed before authentication."""
    config = await system_config_service.get(session)
    return {
        "site_name": getattr(config, "site_name", settings.PROJECT_NAME),
        "logo": getattr(config, "logo", None),
        "allow_registration": bool(getattr(config, "allow_registration", False)),
    }


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(
    user_in: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Create a regular user when public registration is enabled."""
    config = await system_config_service.get(session)
    if not bool(getattr(config, "allow_registration", False)):
        raise HTTPException(status_code=403, detail="Registration is disabled")

    user_data = user_in.model_dump(exclude_none=True)
    user_data.update({"role": "user", "is_active": True, "is_superuser": False})
    from app.core.access import current_actor
    token = current_actor.set(None)
    try:
        return await user_service.create(session, UserCreate(**user_data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        current_actor.reset(token)

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    session: AsyncSession = Depends(get_session), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Find user by email
    statement = select(User).where(User.email == form_data.username)
    result = await session.exec(statement)
    user = result.first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

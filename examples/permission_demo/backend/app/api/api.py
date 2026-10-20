from fastapi import APIRouter
from app.api.endpoints import upload
from app.api.endpoints import login
from app.api.endpoints import ws
from app.api.endpoints import admin_config
from app.api.endpoints import member_only_post
from app.api.endpoints import premium_content
from app.api.endpoints import public_article
from app.api.endpoints import secret_config
from app.api.endpoints import system_config
from app.api.endpoints import user
from app.api.endpoints import user_profile

api_router = APIRouter()

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(admin_config.router, prefix="/admin_config", tags=["admin_config"])
api_router.include_router(member_only_post.router, prefix="/member_only_posts", tags=["member_only_posts"])
api_router.include_router(premium_content.router, prefix="/premium_contents", tags=["premium_contents"])
api_router.include_router(public_article.router, prefix="/public_articles", tags=["public_articles"])
api_router.include_router(secret_config.router, prefix="/secret_config", tags=["secret_config"])
api_router.include_router(system_config.router, prefix="/system_config", tags=["system_config"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(user_profile.router, prefix="/user_profiles", tags=["user_profiles"])
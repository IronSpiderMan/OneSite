from fastapi import APIRouter
from app.api.endpoints import upload
from app.api.endpoints import login
from app.api.endpoints import ws
from app.api.endpoints import admin_settings
from app.api.endpoints import category
from app.api.endpoints import metric
from app.api.endpoints import notification
from app.api.endpoints import product
from app.api.endpoints import system_config
from app.api.endpoints import tag
from app.api.endpoints import user

api_router = APIRouter()

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(admin_settings.router, prefix="/admin_settings", tags=["admin_settings"])
api_router.include_router(category.router, prefix="/categorys", tags=["categorys"])
api_router.include_router(metric.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(notification.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(product.router, prefix="/products", tags=["products"])
api_router.include_router(system_config.router, prefix="/system_config", tags=["system_config"])
api_router.include_router(tag.router, prefix="/tags", tags=["tags"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
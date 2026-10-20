from fastapi import APIRouter
from app.api.endpoints import upload
from app.api.endpoints import login
from app.api.endpoints import ws
from app.api.endpoints import data_model
from app.api.endpoints import data_source
from app.api.endpoints import device
from app.api.endpoints import system_config
from app.api.endpoints import user

api_router = APIRouter()

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(data_model.router, prefix="/data_models", tags=["data_models"])
api_router.include_router(data_source.router, prefix="/data_sources", tags=["data_sources"])
api_router.include_router(device.router, prefix="/devices", tags=["devices"])
api_router.include_router(system_config.router, prefix="/system_config", tags=["system_config"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
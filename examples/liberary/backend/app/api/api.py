from fastapi import APIRouter
from app.api.endpoints import upload
from app.api.endpoints import login
from app.api.endpoints import ws
from app.api.endpoints import author
from app.api.endpoints import book
from app.api.endpoints import subject
from app.api.endpoints import system_config
from app.api.endpoints import user

api_router = APIRouter()

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(author.router, prefix="/authors", tags=["authors"])
api_router.include_router(book.router, prefix="/books", tags=["books"])
api_router.include_router(subject.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(system_config.router, prefix="/system_config", tags=["system_config"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
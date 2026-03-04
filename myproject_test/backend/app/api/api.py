from fastapi import APIRouter
from app.api.endpoints import user, upload

api_router = APIRouter()
# The 'user' endpoint will be generated or linked here. 
# Since we are templating, we can assume user.py exists in endpoints
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(upload.router, tags=["upload"])

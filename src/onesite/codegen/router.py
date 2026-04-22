from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console

console = Console()


def update_api_router(models: List[Dict[str, Any]], api_file_path: Path, scheduled_tasks: List[Dict[str, Any]] = None):
    imports: List[str] = []
    routers: List[str] = []

    imports.append("from app.api.endpoints import upload")
    routers.append('api_router.include_router(upload.router, tags=["upload"])')

    imports.append("from app.api.endpoints import login")
    routers.append('api_router.include_router(login.router, tags=["login"])')

    # WebSocket endpoint (always available for online status tracking)
    imports.append("from app.api.endpoints import ws")
    routers.append('api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])')

    # Add tasks router if scheduled_tasks is configured
    if scheduled_tasks:
        imports.append("from app.api.endpoints import tasks")
        routers.append('api_router.include_router(tasks.router, tags=["tasks"])')

    for model in models:
        imports.append(f"from app.api.endpoints import {model['module_name']}")
        prefix = f"/{model['module_name']}s" if not model.get('is_singleton') else f"/{model['module_name']}"
        tag_name = f"{model['module_name']}s" if not model.get('is_singleton') else f"{model['module_name']}"
        routers.append(
            f'api_router.include_router({model["module_name"]}.router, prefix="{prefix}", tags=["{tag_name}"])'
        )

    content = (
        "from fastapi import APIRouter\n"
        + "\n".join(imports)
        + "\n\napi_router = APIRouter()\n\n"
        + "\n".join(routers)
    )
    api_file_path.write_text(content)
    console.print(f"Updated {api_file_path}")


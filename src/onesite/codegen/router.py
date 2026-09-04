from pathlib import Path
from typing import Any, Dict, List

from .file_utils import write_file_with_status


def update_api_router(
    models: List[Dict[str, Any]],
    api_file_path: Path,
    scheduled_tasks: List[Dict[str, Any]] | None = None,
    tools: List[Dict[str, Any]] | None = None,
    external_resources_enabled: bool = False,
    visualizations_enabled: bool = False,
    import_export_enabled: bool = False,
    custom_api_modules: List[str] | None = None,
    public_dashboard_enabled: bool = False,
):
    imports: List[str] = []
    routers: List[str] = []

    imports.append("from app.api.endpoints import upload")
    routers.append('api_router.include_router(upload.router, tags=["upload"])')

    imports.append("from app.api.endpoints import login")
    routers.append('api_router.include_router(login.router, tags=["login"])')

    imports.append("from app.api.endpoints import video_streams")
    routers.append(
        'api_router.include_router(video_streams.router, prefix="/video-streams", tags=["video-streams"])'
    )

    # WebSocket endpoint (always available for online status tracking)
    imports.append("from app.api.endpoints import ws")
    routers.append('api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])')

    # Add tasks router if scheduled_tasks is configured
    if scheduled_tasks:
        imports.append("from app.api.endpoints import tasks")
        routers.append('api_router.include_router(tasks.router, tags=["tasks"])')

    if tools:
        imports.append("from app.api.endpoints import tools")
        routers.append(
            'api_router.include_router(tools.router, prefix="/tools", tags=["tools"])'
        )

    if import_export_enabled:
        imports.append("from app.api.endpoints import task_center")
        routers.append(
            'api_router.include_router(task_center.router, '
            'prefix="/task-center", tags=["task-center"])'
        )

    if external_resources_enabled:
        imports.append("from app.api.endpoints import external_resources")
        routers.append(
            'api_router.include_router(external_resources.router, prefix="/external-resources", tags=["external-resources"])'
        )

    if visualizations_enabled:
        imports.append("from app.api.endpoints import visualizations")
        routers.append(
            'api_router.include_router(visualizations.router, prefix="/visualizations", tags=["visualizations"])'
        )
    if public_dashboard_enabled:
        imports.append("from app.api.endpoints import public_dashboard")
        routers.append(
            'api_router.include_router(public_dashboard.router, prefix="/public/dashboard", tags=["public-dashboard"])'
        )

    for model in models:
        imports.append(f"from app.api.endpoints import {model['module_name']}")
        prefix = f"/{model['module_name']}s" if not model.get('is_singleton') else f"/{model['module_name']}"
        tag_name = f"{model['module_name']}s" if not model.get('is_singleton') else f"{model['module_name']}"
        routers.append(
            f'api_router.include_router({model["module_name"]}.router, prefix="{prefix}", tags=["{tag_name}"])'
        )

    for index, module in enumerate(custom_api_modules or []):
        module_parts = module.split(".")
        module_name = module_parts[-1]
        package = ".".join(
            ["app", "api", "endpoints", "custom", *module_parts[:-1]]
        )
        alias = f"custom_api_{index}"
        imports.append(f"from {package} import {module_name} as {alias}")
        routers.append(f"api_router.include_router({alias}.router)")

    content = (
        "from fastapi import APIRouter\n"
        + "\n".join(imports)
        + "\n\napi_router = APIRouter()\n\n"
        + "\n".join(routers)
    )
    write_file_with_status(api_file_path, content)

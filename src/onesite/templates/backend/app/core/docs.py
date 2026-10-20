"""Serve Swagger UI using bundled assets, without a CDN dependency."""

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html


def register_docs(app: FastAPI) -> None:
    @app.get("/docs", include_in_schema=False)
    async def swagger_ui(request: Request):
        root_path = request.scope.get("root_path", "").rstrip("/")
        assets = f"{root_path}/static/swagger-ui"
        return get_swagger_ui_html(
            openapi_url=f"{root_path}{app.openapi_url}",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=f"{root_path}{app.swagger_ui_oauth2_redirect_url}",
            swagger_js_url=f"{assets}/swagger-ui-bundle.js",
            swagger_css_url=f"{assets}/swagger-ui.css",
            swagger_favicon_url=f"{assets}/favicon-32x32.png",
            swagger_ui_parameters={"validatorUrl": None},
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_redirect():
        return get_swagger_ui_oauth2_redirect_html()

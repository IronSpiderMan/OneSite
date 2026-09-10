"""OneSite project configuration.

This file is executed by ``site sync``. Keep it as trusted project code and
export exactly one variable named ``config``.
"""

from onesite.config import DesktopConfig, SiteConfig, Timezone, env, sqlite_url


config = SiteConfig(
    project_name=__PROJECT_NAME__,
    database_url=sqlite_url(),
    upload_dir="uploads",
    # Set SECRET_KEY in the shell or deployment environment for production.
    secret_key=env("SECRET_KEY", default="changeme"),
    access_token_expire_minutes=11520,
    extra={"TIMEZONE": Timezone.ASIA_SHANGHAI},
    allowed_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    desktop=DesktopConfig(
        identifier=__DESKTOP_IDENTIFIER__,
        version="0.1.0",
        api_url="http://127.0.0.1:8000/api/v1",
        width=1280,
        height=800,
    ),
)

"""Application-owned resource lifecycle hooks.

Keep connections, clients, and other process-wide resources here. This file is
developer-owned and is copied into the generated backend by ``site sync``.
"""

from fastapi import FastAPI


async def init_resources(app: FastAPI) -> None:
    """Initialize application resources and optionally store them on app.state."""
    pass


async def destroy_resources(app: FastAPI) -> None:
    """Release resources created by init_resources."""
    pass

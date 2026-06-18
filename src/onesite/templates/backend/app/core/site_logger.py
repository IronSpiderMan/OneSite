from typing import Optional

from app.core.db import get_session
from app.models.app_log import AppLog


class SiteLogger:
    async def log(
        self,
        level: str,
        message: str,
        source: str = "",
        user_id: Optional[int] = None,
    ) -> None:
        entry = AppLog(level=level, message=message, source=source, user_id=user_id)
        async for session in get_session():
            session.add(entry)
            await session.commit()
            await session.refresh(entry)

        try:
            from app.core.ws import manager

            await manager.broadcast(
                {
                    "type": "site_log",
                    "data": {
                        "id": entry.id,
                        "level": entry.level,
                        "message": entry.message,
                        "source": entry.source,
                        "created_at": entry.created_at.isoformat(),
                    },
                }
            )
        except Exception:
            pass

    async def debug(
        self, message: str, source: str = "", user_id: Optional[int] = None
    ) -> None:
        await self.log("DEBUG", message, source, user_id)

    async def info(
        self, message: str, source: str = "", user_id: Optional[int] = None
    ) -> None:
        await self.log("INFO", message, source, user_id)

    async def warning(
        self, message: str, source: str = "", user_id: Optional[int] = None
    ) -> None:
        await self.log("WARNING", message, source, user_id)

    async def error(
        self, message: str, source: str = "", user_id: Optional[int] = None
    ) -> None:
        await self.log("ERROR", message, source, user_id)


site_logger = SiteLogger()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.logger import get_logger


logger = get_logger(__name__)

_SCHEMA_MISMATCH_MARKERS = (
    "no such column",       # SQLite
    "no such table",        # SQLite
    "has no column named",  # SQLite INSERT/UPDATE
    "undefined column",     # PostgreSQL
    "does not exist",       # PostgreSQL column errors
    "unknown column",       # MySQL/MariaDB
)


def _is_schema_mismatch(error: OperationalError) -> bool:
    """Return whether an operational error likely means models and DB differ."""
    message = str(getattr(error, "orig", error)).lower()
    return any(marker in message for marker in _SCHEMA_MISMATCH_MARKERS)


def register_error_handlers(app: FastAPI) -> None:
    """Convert database failures into safe, machine-readable API responses."""

    @app.exception_handler(OperationalError)
    async def handle_operational_error(
        request: Request, error: OperationalError
    ) -> JSONResponse:
        logger.error(
            "Database operation failed for %s %s",
            request.method,
            request.url.path,
            exc_info=error,
        )
        if _is_schema_mismatch(error):
            return JSONResponse(
                status_code=503,
                content={
                    "code": "DATABASE_SCHEMA_MISMATCH",
                    "detail": (
                        "The database schema is out of date. Apply the required "
                        "database migration, then retry."
                    ),
                },
            )
        return JSONResponse(
            status_code=503,
            content={
                "code": "DATABASE_UNAVAILABLE",
                "detail": "The database is temporarily unavailable. Please try again later.",
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request, error: SQLAlchemyError
    ) -> JSONResponse:
        logger.error(
            "Database request failed for %s %s",
            request.method,
            request.url.path,
            exc_info=error,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "DATABASE_ERROR",
                "detail": "A database error occurred. Please try again later.",
            },
        )

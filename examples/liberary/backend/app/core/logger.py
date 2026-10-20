import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


def _parse_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    s = str(level or "").strip().upper()
    return getattr(logging, s, logging.INFO)


def setup_logging(
    *,
    log_dir: str = "data/logs",
    level: str | int = "INFO",
    when: str = "midnight",
    backup_count: int = 7,
    console: bool = True,
    filename: str = "app.log",
) -> None:
    root = logging.getLogger()
    root.setLevel(_parse_level(level))
    if getattr(root, "_onesite_configured", False):
        return

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = os.path.join(log_dir, filename)

    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when=when,
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(_parse_level(level))
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(_parse_level(level))
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S")
        )
        root.addHandler(console_handler)

    setattr(root, "_onesite_configured", True)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "app")


setup_logging(
    log_dir=os.getenv("LOG_DIR", "data/logs"),
    level=os.getenv("LOG_LEVEL", "INFO"),
    when=os.getenv("LOG_ROTATE_WHEN", "midnight"),
    backup_count=int(os.getenv("LOG_BACKUP_COUNT", "7")),
    console=os.getenv("LOG_CONSOLE", "true").lower() in {"1", "true", "yes", "y", "on"},
    filename=os.getenv("LOG_FILENAME", "app.log"),
)

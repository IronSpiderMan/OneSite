"""Shared utilities and constants for all pipeline phases."""

from rich.console import Console

from ..metadata.permissions import ROLE_ORDER as ROLE_ORDER
from ..naming import pluralize as pluralize, to_pascal as to_pascal, to_snake as to_snake

console = Console()

ROLE_TO_ENUM = {"user": "USER", "admin": "ADMIN", "developer": "DEVELOPER"}

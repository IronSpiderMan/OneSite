#!/usr/bin/env python3
"""OneSite Studio: independent, local project editor and CLI supervisor.

Run with the Python environment in which OneSite is installed::

    python webui.py [--port 8765] [--projects-dir ./projects] [--no-browser]

Only the Python standard library is needed by this file. OneSite is accessed
in child processes, never imported into the HTTP server. Project Python is
parsed, not executed, when opening, previewing, or saving an editor document.

This file is a backward-compatible entry point. The actual implementation
is in the webui/ package. Use `python -m webui` to run as a module.
"""

from __future__ import annotations

# 向后兼容：导入并运行主入口
from webui.__main__ import main

if __name__ == "__main__":
    main()

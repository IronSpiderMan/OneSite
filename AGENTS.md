# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

OneSite is a model-driven CLI tool that generates full-stack web applications (FastAPI + React/Vite) from SQLModel definitions. The CLI command is `site`.

## Commands

```bash
# Create a new project
site create <project_name>

# Sync models and generate code (run from project directory)
site sync [--install/-i]

# Run backend/frontend/all
site run [backend|frontend|all]

# Build Docker images
site build [--component/-c] [--engine/-e] [--tag/-t] [--port/-p]

# Run docker-compose commands
site compose up -d
site compose down
site compose logs -f
```

## Architecture

### Source Structure

```
src/onesite/
├── main.py              # CLI entry point (Typer commands: create, sync, run, build, compose)
├── generator.py         # Code generation orchestrator
├── codegen/             # Core code generation
│   ├── pipeline.py      # Main generation pipeline - orchestrates all codegen
│   ├── introspect.py    # SQLModel introspection - extracts field metadata, FK relations, permissions
│   ├── render.py        # Jinja2 template rendering
│   ├── config.py        # site_config.json loader
│   ├── theme.py         # UI theme definitions (normal, industrial, neuron)
│   ├── i18n.py          # Internationalization (EN/ZH)
│   ├── assets.py         # Static asset synchronization
│   ├── router.py        # FastAPI router generation
│   └── envsync.py       # Environment file synchronization
└── templates/
    ├── codegen/          # Jinja2 templates (.j2 files) for code generation
    ├── backend/          # Backend template files
    ├── frontend/         # Frontend template files
    └── models/           # Base model templates (User, etc.)
```

### Code Generation Flow (`site sync`)

1. Load `site_config.json`
2. Sync env files to backend/.env and frontend/.env
3. Copy `models/*.py` → `backend/app/models/`
4. Import models and introspect via `get_model_fields()` in `introspect.py`
5. Build model metadata (FK relations, M2M, search fields)
6. Generate backend: schemas → cruds → services → API endpoints
7. Generate frontend: services → stores → pages → routes → menu
8. Generate i18n locale files and theme CSS
9. Sync UI components and static assets

### Three-Layer Permission System

Permissions use a three-layer design: model-level, field-level, and frontend visibility.
Each layer is independently configured and orthogonal.

**Permission chars:** `c` = create, `r` = read, `u` = update, `d` = delete

#### Layer 1 — Model-level CRUD

Controls which roles can call each API endpoint and see corresponding buttons.

```python
__onesite__ = {
    "permissions": {
        "developer": "crud",   # full access
        "admin": "crud",       # full access
        "user": "r",           # read-only
    }
}
```

- Dict format: specify per-role, missing roles get `""` (no access)
- String format (legacy): `"admin-crud"` → admin+ have `crud`, users get `""`
- Default: all roles get `"crud"` (full access)

Generated effect:
- API endpoints get `deps.require_role(deps.UserRole.XX)` at the minimum level
- Frontend list/detail pages check `role_permissions[userRole]` at runtime for button visibility

#### Layer 2 — Field-level CRU

Controls field inclusion in schemas and forms. No `d` at field level (delete is model-level only).

```python
Field(sa_column_kwargs={
    "info": {"site_props": {
        "permissions": {
            "developer": "cru",
            "admin": "cru",
            "user": "r",       # user can only read this field
        }
    }}
})
```

- `c` = field in Create schema / create form
- `r` = field in Read/Response schema / displayed in detail
- `u` = field in Update schema / edit form
- Inherits from model-level by default, strips `d`
- Special field defaults: `id`/`created_at` → `r`, `updated_at` → `ru`

#### Layer 3 — Frontend Visibility

Controls which roles see the model in navigation menus.

```python
__onesite__ = {
    "visible": ["admin", "developer"],  # list format (new)
    # or: "visible": {"user": False, "admin": True, "developer": True}
    # or: "visible": "admin"  (string, admin+ visible)
}
```

- Default: derived from model permissions (visible if role has any permission)
- Explicit config overrides the default entirely
- Independent from API access — a model can be menu-hidden but still accessible via URL

#### Full Example

```python
class PremiumContent(SQLModel, table=True):
    __onesite__ = {
        "permissions": {"user": "", "admin": "crud", "developer": "crud"},
        "visible": ["admin", "developer"],
    }
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(sa_column_kwargs={"info": {"site_props": {"permissions": {"user": "r", "admin": "cru", "developer": "cru"}}}})
```

See `examples/permission_demo/` for a comprehensive demonstration.

### Generated Project Structure

```
<project>/
├── site_config.json      # Project configuration
├── models/               # SQLModel definitions (source of truth)
├── backend/
│   ├── app/
│   │   ├── api/endpoints/  # REST endpoints per model
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── cruds/          # CRUD operations
│   │   └── models/         # Synced models
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/<model>/  # List and detail pages
    │   ├── services/        # API service functions
    │   └── stores/          # Zustand stores
    └── package.json
```

### Model Conventions

- Table names auto-convert to snake_case (`UserProfile` → `user_profile`)
- FK fields named `{target}_id` are auto-detected
- Image fields: names containing `image`, `avatar`, `photo`, or `_image` suffix
- File fields: names containing `file`, `attachment`, or `_file` suffix
- M2M link tables require `__onesite__ = {"is_link_table": True}`

### site_props Configuration

Model-level in `__onesite__` or `__table_args__.info.site_props`:
- `is_link_table`, `is_singleton`, `frontend_only`, `is_notification_table`
- `permissions`: dict `{"user": "crud", "admin": "crud", "developer": "crud"}` or legacy string
- `visible`: list `["admin", "developer"]`, dict, or string — frontend menu visibility
- `translations`: `{"zh": {...}, "en": {...}}`
- `actions`: custom action buttons
- `special_me_permissions`: dict `{"user": "ru"}` — special /me endpoint perms

Field-level in `sa_column_kwargs.info.site_props`:
- `permissions`: dict `{"user": "cru", "admin": "cru", "developer": "cru"}` or string like `"cru"`
- `is_search_field`: enable filter
- `is_foreign_key`, `reverse_display`: FK handling
- `component`: "image", "file", "json"
- `create_optional`, `update_optional`: form field requirements

### Testing

Generated projects create test directories alongside each project. There are no unified test commands in the CLI itself - tests are framework-specific (pytest for backend, vitest/npm test for frontend).

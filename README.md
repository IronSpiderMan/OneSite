# OneSite

[中文文档](README.zh-CN.md) · [Training guide](docs/onesite-training-guide.md)

OneSite is a model-driven CLI that generates an admin-style full-stack application from SQLModel definitions. `app/models/` is the source of truth; `site sync` generates FastAPI schemas, CRUD, services and REST endpoints, plus React/Vite pages, API clients, navigation, translations and theme assets under `generated/`.

## Requirements and installation

- Python 3.10+
- Node.js and npm for generated frontends
- Docker or Podman only when building containers

```bash
pip install onesite
site --help
```

For development in this repository:

```bash
python -m pip install -e .
```

## Quick start

```bash
site create inventory
cd inventory

# Add or edit SQLModel classes in app/models/.
site sync --install
site run
```

The frontend is available at `http://localhost:5173`; FastAPI documentation is at `http://localhost:8000/docs`. A new project seeds `admin@example.com` / `admin`; change this credential before deploying.

The normal edit/generate loop is:

```text
edit app/models/, app/integrations/, app/utils/ or site_config.json → site sync → test /docs and the frontend
```

Do not treat `generated/backend/app/models/` as the model source of truth: it is synced from `app/models/`. Everything under `generated/` is replaceable output. Keep durable business customizations in `app/`, not solely in generated files. Existing projects with top-level `models/`, `backend/`, and `frontend/` remain supported without an automatic directory migration.

## CLI

| Command | Purpose |
| --- | --- |
| `site init` | Initialize `site_config.json`, base models and icon reference in the current directory. |
| `site create <project_name>` | Create a new full-stack project. |
| `site sync` | Copy application source and regenerate `generated/backend` and `generated/frontend`. |
| `site sync --install` / `-i` | Regenerate, then install backend and frontend dependencies. |
| `site run` | Run backend and frontend. |
| `site run --component backend` | Run only FastAPI. |
| `site run --component frontend` | Run only Vite. |
| `site run <project_path> --component all` | Run a project from another directory. |
| `site build [-c backend\|frontend\|all] [-e docker\|podman] [-t TAG] [--development\|--production] [-p PORT]` | Build tagged images and generate `deploy/docker-compose.yml`; production compiles the backend with Nuitka. |
| `site build --component desktop` | Build a native Tauri client for the current macOS or Windows host. |
| `site compose [--engine docker\|podman] up -d` | Run Compose using `deploy/docker-compose.yml`. |

`component` is an option: use `site run --component backend`, not `site run backend`.

## Project configuration

`site_config.json` is created with sensible defaults. Common settings are:

```json
{
  "project_name": "Inventory",
  "database_url": "sqlite:///./app.db",
  "upload_dir": "uploads",
  "secret_key": "replace-with-a-random-production-secret",
  "access_token_expire_minutes": 11520,
  "extra": {
    "TIMEZONE": "Asia/Shanghai"
  },
  "allowed_origins": ["http://localhost:5173", "http://localhost:3000"],
  "desktop": {
    "identifier": "com.example.inventory",
    "version": "1.0.0",
    "api_url": "https://api.example.com/api/v1",
    "width": 1280,
    "height": 800
  },
  "style": "normal",
  "radius": 1.0,
  "nav_order": ["user", "category", "product"]
}
```

Supported themes are `normal`, `industrial`, `anime`, `cute`, `emqx` and `neuron`. The `neuron` theme is a dark telemetry-console style with a graphite grid and signal-green accents. Use a production database URL and a strong, private `secret_key` outside local development.

Every key under `extra` is synchronized to the backend `.env`. `TIMEZONE`
accepts an IANA timezone name, defaults to `Asia/Shanghai`, controls the
default frontend display timezone and APScheduler cron timezone, while
datetimes are normalized to UTC before database persistence.

`desktop.api_url` must be an absolute HTTP(S) URL because a packaged desktop
client cannot use Vite's development proxy. `site sync` adds the exact Tauri
origins to the generated backend CORS configuration.

### MQTT callbacks

Keep broker settings and topic bindings in `site_config.json`:

```json
{
  "mqtt": {
    "url": "mqtt://localhost:1883",
    "username": "admin",
    "password": "public",
    "client_id": "onesite_backend",
    "callbacks": [
      {
        "topic": "alarm-trigger/alarms/#",
        "handler": "on_alarm",
        "qos": 1
      }
    ]
  }
}
```

On `site sync`, OneSite looks for
`app/integrations/mqtt/on_alarm.py`. If the directory or file does not exist, it
creates a starter handler:

```python
async def on_alarm(topic: str, payload: str):
    # TODO: Implement your business logic here
    pass
```

`app/integrations/mqtt/` is developer-owned source. It is mirrored into
`generated/backend/app/integrations/mqtt/` on every sync, so an existing source handler
always overwrites its generated backend copy. Do not make durable changes only
in the backend copy. OneSite generates `generated/backend/app/core/mqtt_bindings.py` from
the callback list to register handlers; handler modules should implement the
function and do not need to register themselves.

Each callback requires a non-empty `topic` and a handler that is a valid Python
identifier. `qos` is optional, defaults to `1`, and accepts `0`, `1`, or `2`.
The same handler may be bound to multiple topics. For production deployments,
override MQTT credentials through `MQTT_URL`, `MQTT_USERNAME`,
`MQTT_PASSWORD`, and `MQTT_CLIENT_ID` rather than committing secrets.

### Dashboard tools

Project tools add configuration-driven forms to the Dashboard and execute the
developer implementation in the background:

```json
{
  "tools": [
    {
      "name": "merge_reports",
      "title": "Merge reports",
      "description": "Upload CSV files and merge them in the background",
      "permissions": ["admin", "developer"],
      "execution": {"mode": "background", "timeout_seconds": 600},
      "inputs": [
        {
          "name": "copies",
          "type": "number",
          "number_kind": "int",
          "label": "Copies",
          "default": 1,
          "min": 1
        },
        {
          "name": "files",
          "type": "files",
          "label": "CSV files",
          "required": true,
          "accept": [".csv"],
          "max_files": 10,
          "max_size_mb": 20
        }
      ],
      "result": {"type": "file"}
    }
  ]
}
```

On the first `site sync`, OneSite scaffolds `app/tools/merge_reports.py` and
mirrors it to `generated/backend/app/tools/merge_reports.py`. Only edit the
developer-owned source file:

```python
from app.core.tool_runtime import ToolContext, ToolResult


async def merge_reports(
    *,
    copies: int,
    files: list[str],
    context: ToolContext,
) -> ToolResult:
    await context.set_progress(10, "Reading files")
    output = context.output_path("merged.csv")
    # Implement the merge and write output here. File inputs are local paths.
    await context.set_progress(90, "Finalizing")
    return ToolResult(
        message="Merge completed",
        data={"copies": copies},
        download_path=output,
    )
```

Supported input types are `str`, `text`, `number`, `bool`, `select`,
`multi_select`, `date`, `datetime`, `file`, `files`, and `json`. The submit API
also accepts the aliases `string`, `boolean`, and `list`, normalizing them to
`str`, `bool`, and `multi_select` respectively. It stores uploaded files before
publishing to the in-process task queue. Execution
state is persisted in `onesite_background_execution`; WebSocket messages update the
Dashboard immediately, while the status API lets the UI recover after refresh
or reconnection. The current queue remains process-local, so queued work does
not provide distributed delivery across multiple backend instances.

### Scheduled tasks

Scheduled tasks use the same developer-owned source and background execution
model. A scheduler trigger creates an execution record and publishes work to
the task queue; it does not run business code inside the scheduler callback.

```json
{
  "scheduled_tasks": [
    {
      "name": "daily_summary",
      "title": "Daily summary",
      "schedule": {"type": "cron", "cron": "0 8 * * *"},
      "enabled": true,
      "timeout_seconds": 600,
      "overlap": "skip",
      "manual_permissions": ["admin", "developer"],
      "params": [
        {"name": "region", "type": "str", "default": "cn"},
        {"name": "include_inactive", "type": "bool", "default": false}
      ],
      "notify": {
        "on_success": false,
        "on_failure": true,
        "roles": ["developer"]
      }
    }
  ]
}
```

An interval schedule uses `{"type": "interval", "seconds": 300}`. Legacy
`cron`, `interval`, and object-shaped `params` remain supported and are
normalized during generation.
Scheduled-task parameters accept both the concise names used by tools
(`str`, `bool`, and `multi_select`) and their descriptive aliases (`string`,
`boolean`, and `list`); aliases are normalized to the concise names.

The first `site sync` creates `app/tasks/daily_summary.py`:

```python
from app.core.scheduled_task_runtime import (
    ScheduledTaskContext,
    ScheduledTaskResult,
)


async def daily_summary(
    *,
    region: str,
    include_inactive: bool,
    context: ScheduledTaskContext,
) -> ScheduledTaskResult:
    await context.set_progress(10, "Reading data")
    # Implement the task here.
    return ScheduledTaskResult(message="Summary completed")
```

`site sync` mirrors this source to `generated/backend/app/tasks/`, generates a
separate binding module, and validates the handler signature. Existing handlers
from the older generated-only layout are migrated into the developer source
directory; handlers without `context` remain callable for compatibility.

Manual runs return `202 Accepted` with an execution id. Scheduled and manual
runs share progress, timeout, result, history, failure notification and
WebSocket infrastructure. `overlap` supports `skip` and `queue`.

### Developer utilities

Place reusable backend helpers in `app/utils/`:

```text
app/utils/
├── __init__.py
├── formatting.py
└── data/
    └── defaults.json
```

During `site sync`, OneSite recursively mirrors this directory to
`generated/backend/app/utils/`. Source files overwrite their generated copies,
and files removed from the source are removed from the generated directory.
OneSite creates `__init__.py` when needed and skips `__pycache__` and `.pyc`
files. Import utilities in backend code with paths such as
`from app.utils.formatting import format_alarm`.

Legacy projects may continue using top-level `utils/`, which is mirrored to
`backend/app/utils/`.

## Model basics

```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Product(SQLModel, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "商品",
                "fields": {"name": "名称", "price": "价格"},
            },
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    price: float = 0
    is_active: bool = True
```

Field types, requiredness, defaults, enums and unique constraints become API validation and form controls. Fields named like `image`, `avatar`, `photo`, `*_image` use the image uploader; `file`, `attachment`, `*_file` use the file uploader. Override detection with `site_props.component`: `image`, `images`, `file`, `textarea`, `json` or `location`. Use `images` with a JSON-backed `list[str]` field to upload multiple images.

For a browser-assisted latitude/longitude field, use the bundled `Location`
value object with a JSON column and `component: "location"`:

```python
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.location import Location


class Store(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location: Optional[Location] = Field(
        default=None,
        sa_column=Column(
            JSON,
            nullable=True,
            info={"site_props": {"component": "location"}},
        ),
    )
```

The generated form accepts manual coordinates, provides a **Use current
location** button backed by the browser Geolocation API, and can open an
OpenStreetMap map for click-to-select positioning. Browser geolocation requires
user permission and, outside localhost, a secure HTTPS context. Existing
projects should run `site sync -i` once to install the Leaflet dependencies.
The default raster tiles use the official OpenStreetMap endpoint. Deployments
can override it with `VITE_MAP_TILE_URL` and `VITE_MAP_ATTRIBUTION` in the
frontend build environment.

### Transactional CUD hooks

Models can define service-level hooks around create, update and delete operations:

```python
class Order(SQLModel, table=True):
    # fields ...

    async def on_before_update(self, session, old, changes, context):
        if old["status"] == "completed":
            raise ValueError("Completed orders cannot be changed")

    async def on_after_update(self, session, old, context):
        session.add(OrderAudit(order_id=self.id, action="updated"))

    async def on_after_commit_update(self, old, context):
        # The database transaction is already committed here.
        pass
```

`on_before_create/update/delete` and `on_after_create/update/delete` run in the same transaction as the CUD operation. The generated service commits only after they succeed and rolls back on any exception. A hook may declare only the named arguments it needs: `session`, `old`, `changes`, or `context`. `context` contains `operation`, `input_data`, and `changed_fields`.

`on_after_commit_create/update/delete` runs after commit; failures are logged and cannot roll back the database. Use a transactional outbox rather than direct email, HTTP or message-broker calls when reliable external delivery is required.

Explicit background hooks use `on_background_after_create/update/delete`. They
are queued only after the database commit succeeds and run with a fresh
`AsyncSession`. They may declare the same named arguments as the corresponding
post-commit hook, plus `session`. Background failures are logged and cannot
roll back the original CUD operation.

```python
async def on_background_after_create(self, session, context):
    session.add(DeliveryJob(order_id=self.id))
```

Low-level SQLAlchemy mapper hooks use the explicit
`on_orm_before_insert/update/delete` and
`on_orm_after_insert/update/delete` names and must be synchronous `def`
methods. The ambiguous legacy `on_before_insert` and `on_after_insert` aliases
emit a deprecation warning; async legacy/ORM hooks are rejected during
`site sync` instead of being silently converted into background work.

| Hook family | Execution | Can roll back the CUD transaction? |
|---|---|---|
| `on_before/after_create/update/delete` | Same transaction | Yes |
| `on_after_commit_create/update/delete` | Inline, after commit | No |
| `on_background_after_create/update/delete` | Background, after commit | No |
| `on_orm_before/after_insert/update/delete` | SQLAlchemy mapper event | Low-level; use with care |

### Business primary keys

Integer IDs with `default=None` are database-generated and are not accepted by the create API by default. A business key can be passed on creation by making the `id` field required and explicitly granting it create permission:

```python
class Device(SQLModel, table=True):
    id: str = Field(
        primary_key=True,
        nullable=False,
        sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}},
    )
    name: str
```

OneSite generates `id: str` consistently in its create/read schemas, endpoint paths, CRUD/service functions and frontend client for this model. Primary keys are immutable through the normal update API.

### Relations

Foreign keys are inferred from a `{target}_id` field with `foreign_key="target.id"`:

```python
category_id: Optional[int] = Field(default=None, foreign_key="category.id")
```

The generated UI selects and displays related labels. Make a useful target label field `unique=True` and/or `is_search_field=True`.

For many-to-many relations, mark the link table:

```python
class ProductTagLink(SQLModel, table=True):
    __onesite__ = {"is_link_table": True}
    product_id: Optional[int] = Field(default=None, primary_key=True, foreign_key="product.id")
    tag_id: Optional[int] = Field(default=None, primary_key=True, foreign_key="tag.id")
```

Link tables with only relation keys become multi-select fields; extra fields keep standalone CRUD support. Self-referencing FKs can generate a tree view.

## `__onesite__` model configuration

Place model-level options in `__onesite__` (or table `info.site_props`). Key options include:

| Option | Effect |
| --- | --- |
| `translations` | Model, field and enum labels for `zh`/`en`. |
| `icon` | Lucide icon name for navigation. |
| `permissions` | Model CRUD permissions by role. |
| `visible` | Navigation visibility by role. |
| `owner_field` | User-owned resource filtering, e.g. `"owner_id"`. |
| `is_link_table` | Marks a many-to-many link table. |
| `is_singleton` | Creates a single configuration-like record UI/API. |
| `frontend_only` | Excludes a model from backend persistence. |
| `page_edit` | Use a full page rather than dialogs for create/edit. |
| `actions` | Adds permission-controlled custom action buttons. |
| `importable` / `exportable` | Enables CSV import/export flows. |
| `import_key` | Field used for import upsert matching. |
| `refresh_interval` | Enables periodic list refresh. |
| `visualize` | Adds generated dashboard statistics/charts. |
| `is_notification_table` | Enables notification-center behavior and realtime push. |
| `time_series_table` | Configures TimescaleDB/time-series generation. |

Useful field-level `site_props` are `permissions`, `is_search_field`, `component`, `create_optional`, `update_optional`, `is_foreign_key`, `reverse_display`, `allow_download`, `group`, `fixed_keys` and `lock_keys`.

## Permissions and visibility

Permissions are independent at three layers:

1. Model CRUD controls endpoint and button access: `c`, `r`, `u`, `d`.
2. Field CRU controls a field's presence in create, read and update schemas/forms: `c`, `r`, `u`.
3. `visible` controls whether the model appears in navigation.

```python
class PremiumContent(SQLModel, table=True):
    __onesite__ = {
        "permissions": {"user": "", "admin": "crud", "developer": "crud"},
        "visible": ["admin", "developer"],
    }
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(sa_column_kwargs={"info": {"site_props": {
        "permissions": {"user": "r", "admin": "cru", "developer": "cru"},
    }}})
```

Roles are `user`, `admin`, `developer` (in ascending hierarchy). A model permission not specified for a role is no access; an unset model permission defaults to full CRUD for all roles. Field permissions inherit the model permissions without `d`. The implicit defaults are `id`: hidden, `created_at`: read, `updated_at`: read/update; explicitly set field permissions override them.

`owner_field` adds server-side ownership protection: non-admin users only list, read, update and delete their own records, and creation assigns their own user ID.

## Generated capabilities

- JWT authentication and role-based access control
- REST CRUD, unique-constraint validation, list search and filters
- Image/file upload and download controls
- JSON fields, including structured Pydantic-model editors and lockable keys
- Foreign-key label display, M2M selectors, tree views and owner-scoped resources
- Custom actions with role permissions and conditional field updates
- CSV import/export with import-key upserts
- Singleton/configuration models
- Notification center and WebSocket real-time updates
- Dashboard statistics/charts and configurable auto-refresh
- Scheduled jobs via APScheduler with UI management
- EN/ZH locale generation and four built-in themes
- Docker/Podman images and generated Compose configuration
- Optional time-series/TimescaleDB flows

## Container deployment

After syncing a project, build and start it:

```bash
# Regular Python backend (the default)
site build --development --engine docker --tag v1 --port 3000

# Nuitka-compiled Python backend
site build --production --engine docker --tag v1 --port 3000

site compose up -d
site compose logs -f
```

The tag is applied to both `<project>-backend` and `<project>-frontend`. `site build` writes `deploy/docker-compose.yml`. `site create`, `site init`, and `site sync` ensure that `deploy/.env.example` exists; copy it to `deploy/.env` for deployment-specific overrides. `site compose` automatically passes that `.env` file when present. PostgreSQL is included when `database_url` starts with `postgresql`; configure production credentials and API origins before exposing the application. A legacy root-level `docker-compose.yml` remains supported when no deploy Compose file exists.

Generated backend Dockerfiles use the Tsinghua TUNA PyPI mirror, upgrade
pip/setuptools/wheel before installing dependencies, and apply extended retry
and timeout settings to tolerate slower container networks. Production builds
compile with Nuitka in a Python builder stage, then run the standalone output
on `debian:bookworm-slim` without installing Python in the final image. The
system CA bundle is copied from the builder so outbound HTTPS remains usable.

## Desktop builds

`site sync` generates a Tauri 2 shell under `generated/frontend/src-tauri`.
Install dependencies once, configure the remote FastAPI endpoint, and build on
the platform that will run the client:

```bash
site sync --install
site build --component desktop
```

On macOS this produces `.app` and `.dmg` bundles; on Windows it produces an
NSIS installer. OneSite intentionally builds only for the current host—use a
macOS machine for macOS artifacts and a Windows machine for Windows artifacts.
macOS requires Rust and Xcode Command Line Tools. Windows requires Rust with
the MSVC toolchain, Microsoft C++ Build Tools, and WebView2. Release bundles are
written under `generated/frontend/src-tauri/target/release/bundle/`.

## Generated project layout

```text
project/
├── site_config.json
├── app/                       # developer-owned source
│   ├── models/                # SQLModel source of truth
│   ├── integrations/
│   │   └── mqtt/              # MQTT handler implementations
│   ├── tools/                  # Dashboard tool implementations
│   ├── tasks/                  # scheduled task implementations
│   └── utils/                 # reusable developer-owned backend helpers
├── generated/                 # replaceable OneSite output
│   ├── backend/
│   │   ├── Dockerfile
│   │   └── app/
│   │       ├── api/endpoints/
│   │       ├── schemas/ cruds/ services/
│   │       └── models/        # synced model copy
│   └── frontend/
│       ├── Dockerfile
│       ├── src-tauri/          # generated Tauri 2 desktop shell
│       └── src/
│           ├── pages/ services/ stores/
│           └── components/
├── deploy/
│   ├── .env.example
│   ├── .env                   # optional, developer-created and gitignored
│   └── docker-compose.yml     # generated by site build
└── site_config.json
```

See the [Chinese training guide](docs/onesite-training-guide.md) and `examples/` for end-to-end model examples, including permissions and IoT/time-series scenarios.

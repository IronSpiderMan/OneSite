# OneSite

[中文文档](README.zh-CN.md) · [Design principles](docs/design-principles.md)

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
uv sync --group dev
uv run pytest
uv run ruff check src/onesite src/onesite_runtime tests
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
edit app/models/, app/integrations/, app/utils/, app/resources.py or site_config.py → site sync → test /docs and the frontend
```

Do not treat `generated/backend/app/models/` as the model source of truth: it is synced from `app/models/`. Everything under `generated/` is replaceable output. Keep durable business customizations in `app/`, not solely in generated files. Projects must use the `app/` and `generated/` layout; top-level `models/`, `backend/`, and `frontend/` directories are not supported.

## CLI

| Command | Purpose |
| --- | --- |
| `site init` | Initialize `site_config.py`, base models and icon reference in the current directory. |
| `site create <project_name>` | Create a new full-stack project. |
| `site sync` | Copy application source and regenerate `generated/backend` and `generated/frontend`. |
| `site sync --install` / `-i` | Regenerate, then install backend and frontend dependencies. |
| `site sync --build-cmd` | Regenerate, build command projects, and copy their executables to `generated/backend/bin/`. |
| `site run` | Run backend and frontend. |
| `site run --component backend` | Run only FastAPI. |
| `site run --component frontend` | Run only Vite. |
| `site run <project_path> --component all` | Run a project from another directory. |
| `site run --host 0.0.0.0` | Expose the backend and frontend development servers on all network interfaces. |
| `site build [-c backend\|frontend\|all] [-e docker\|podman] [-t TAG] [--development\|--production] [-p PORT]` | Build tagged images and generate `deploy/docker-compose.yml`; production compiles the backend with Nuitka. |
| `site build --component desktop` | Build a native Tauri client for the current macOS or Windows host. |
| `site compose [--engine docker\|podman] up -d` | Run Compose using `deploy/docker-compose.yml`. |

`component` is an option: use `site run --component backend`, not `site run backend`. Use `--host 0.0.0.0` to access the development servers from other devices on the network.

### Command executables

Developer-owned command projects can live in `app/cmd/<name>/`. Put a
`build.sh` in each project on macOS/Linux or a `build.bat` on Windows. When
`site sync --build-cmd` runs, OneSite executes the platform-specific script
from that project directory and expects it to create `<name>` (or `<name>.exe`)
in the same directory. The executable is then copied to
`generated/backend/bin/`. Projects without a build script for the current
platform are skipped. Regular `site sync` does not build command projects.

## Project configuration

`site_config.py` is created with sensible defaults. It uses typed configuration
objects, so VS Code, PyCharm, and other Python-aware editors can complete keys
and validate nested values while you edit:

```python
from onesite.config import DesktopConfig, NavBuiltin, NavGroup, NavModel, SiteConfig, Theme

config = SiteConfig(
    project_name="Inventory",
    database_url="sqlite:///./app.db",
    secret_key="replace-with-a-random-production-secret",
    extra={"TIMEZONE": "Asia/Shanghai"},
    allowed_origins=["http://localhost:5173", "http://localhost:3000"],
    style=Theme.NORMAL,
    radius=1.0,
    desktop=DesktopConfig(
        identifier="com.example.inventory",
        version="1.0.0",
        api_url="https://api.example.com/api/v1",
        width=1280,
        height=800,
    ),
    navigation=[
        NavBuiltin.dashboard(),
        NavGroup(
            key="catalog",
            label={"zh": "商品管理", "en": "Catalog"},
            icon="Package",
            default_open=True,
            children=[NavModel(model="category"), NavModel(model="product")],
        ),
    ],
)
```

`site_config.json` remains supported for existing projects. Do not keep both
files in one project: `site sync` stops with a clear error rather than choosing
one implicitly. A Python configuration is trusted project code and is executed
by `site sync`; use `env("SECRET_KEY")` from `onesite.config` for production
secrets rather than committing them to the file.

Supported themes are `normal`, `industrial`, and `neuron`. The `style` value is a build-time structural theme: `site sync` selects that theme's list, detail, create, dashboard, settings, profile, singleton, and CSS templates. Theme templates live under `src/onesite/templates/codegen/themes/<style>/` and fall back to the shared codegen templates when an override is absent. The `normal` theme uses Ant Design 6 through generated compatibility adapters and only adds the `antd` dependency to normal builds. Light/dark/system mode remains a browser-side runtime preference and is synchronized with Ant Design's theme algorithm. The `neuron` theme is a dark telemetry-console style with a graphite grid and signal-green accents. Use a production database URL and a strong, private `secret_key` outside local development.

Every key under `extra` is synchronized to the backend `.env`. `TIMEZONE`
accepts an IANA timezone name, defaults to `Asia/Shanghai`, controls the
default frontend display timezone and APScheduler cron timezone, while
datetimes are normalized to UTC before database persistence.

### Navigation

`navigation` is the ordered, declarative sidebar tree. A `model` entry refers
to the model's `module_name`; a `group` is a non-routable, collapsible second-
level container; and `builtin` supports `dashboard`, `reports`,
`external-resources`, and `task-center`. Group
labels require `zh` and `en` translations. Model
permissions and `visible` settings still control whether each child is shown;
empty groups are hidden automatically. Models omitted from an explicitly
configured tree remain reachable by route and API but are not shown in the
sidebar.

### Application resources

Put process-wide application resources, such as HTTP clients, connection pools,
or device SDK handles, in `app/resources.py`. OneSite creates this file for new
and existing projects and copies it to the generated backend on `site sync`.
Both hooks are async and receive the FastAPI application, so resources can be
stored on `app.state`:

```python
from fastapi import FastAPI
from httpx import AsyncClient

async def init_resources(app: FastAPI) -> None:
    app.state.http = AsyncClient()

async def destroy_resources(app: FastAPI) -> None:
    await app.state.http.aclose()
```

The generated `main.py` invokes these hooks from FastAPI's `lifespan`:
initialization runs after OneSite's built-in infrastructure starts, and cleanup
runs before that infrastructure is shut down. Keep the two function names and
the `app` parameter unchanged; `site sync` validates their signatures.

### External resource providers

One provider represents one external system and can own many resource kinds.
Map each resource kind to one model:

```python
class Camera(SQLModel, table=True):
    __onesite__ = {
        "external_resource": {
            "provider": "edgeflow",
            "resource": "cameras",
            # Optional; defaults to "id".
            "identity": "id",
        }
    }
```

Register the provider module in `site_config.py`:

```python
config = SiteConfig(
    ...,
    providers={
        "edgeflow": ExternalResourceProviderConfig(module="edgeflow")
    },
)
```

The first `site sync` creates the developer-owned
`app/providers/edgeflow.py`. Its provider implements `create(resource,
payload)`, `update(resource, payload, previous)`, `delete(resource, payload)`,
and `reconcile(desired)`. External-resource CUD runs as a hidden transactional
`on_after_*` hook: provider failure rolls back the local change. A periodic
backend reconciliation converges every provider after timeouts, process
crashes, or external drift. The management page exposes provider-level health
and aggregate reconciliation counters rather than per-resource tasks.

The `resource_type` and `identity_field` declaration names remain accepted as aliases.

`desktop.api_url` must be an absolute HTTP(S) URL because a packaged desktop
client cannot use Vite's development proxy. `site sync` adds the exact Tauri
origins to the generated backend CORS configuration.

### MQTT callbacks

Keep broker settings and topic bindings in `site_config.py` (the JSON shape below is also accepted by legacy `site_config.json` projects):

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

### Custom frontend features and Dashboard widgets

Developer-owned frontend features live in
`app/frontend/features/<feature_name>/`. Each feature exports a typed manifest
from `feature.py`; its components, services, stores, locale files, and other
assets are mirrored to `generated/frontend/src/custom/` during `site sync`.

```python
from onesite.frontend import (
    DashboardWidget,
    FrontendFeature,
    FrontendMenu,
    FrontendOverride,
    FrontendRoute,
)

feature = FrontendFeature(
    name="operations",
    routes=[
        FrontendRoute(
            id="workspace",
            path="/operations",
            component="pages/Workspace.tsx",
            access=["admin", "developer"],
            menu=FrontendMenu(
                title={"zh": "运营工作台", "en": "Operations"},
                icon="Activity",
            ),
        ),
        FrontendRoute(
            id="public_status",
            path="/public/status",
            component="pages/PublicStatus.tsx",
            layout="public",
        ),
    ],
    overrides=[
        FrontendOverride(
            target="model.sync_task.detail",
            component="pages/CustomSyncTask.tsx",
        ),
    ],
    dashboard_widgets=[
        DashboardWidget(
            id="health",
            component="components/HealthWidget.tsx",
            title={"zh": "运行健康度", "en": "Operations Health"},
            span={"md": 12, "xl": 6},
            access=["admin", "developer"],
        ),
    ],
    dependencies={"dayjs": "^1.11.0"},
)
```

Application routes are mounted inside the authenticated generated layout and
can restrict frontend access by role. Public routes are mounted outside that
layout and do not require a token. To place a menu-enabled custom route in an
explicit navigation tree, reference its namespaced ID:

```python
from onesite.config import NavGroup, NavRoute

NavGroup(
    key="operations",
    label={"zh": "运营", "en": "Operations"},
    children=[NavRoute(route="operations.workspace")],
)
```

Generated routes have stable override targets such as `builtin.dashboard`,
`builtin.settings`, `model.device.list`, `model.device.detail`, and
`model.device.create`. Overrides replace only the rendered component, keeping
the generated URL and navigation contract. Route IDs, paths, referenced
components, navigation references, role declarations, and override targets
are validated during sync.
Frontend `access` only controls navigation and route rendering; backend API
permissions remain the security boundary for feature data and operations.

Widget IDs are namespaced as `<feature>.<widget>`. The generated Dashboard
orders widgets by `order`, filters them by the current role, provides a
theme-owned card frame by default, and uses the declared responsive 12-column
span. Set `frame=False` when the component supplies its own complete surface.
Locale files at `locales/en.json` and `locales/zh.json` are automatically merged
below `features.<feature_name>`, so feature components can use keys such as
`t('features.operations.status')`. Declared npm dependencies are merged into the
generated `package.json`; incompatible versions fail during sync instead of
silently replacing generator dependencies.

See `examples/datahub/app/frontend/features/ops_dashboard/` for a complete
multi-page feature with authenticated and public routes, a generated-page
override, two Dashboard widgets, a shared Zustand store, a service,
translations, and deterministic mock data.

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

Project utilities belong in `app/utils/` and are mirrored to
`generated/backend/app/utils/`.

### Custom backend APIs, services, and CRUDs

Keep developer-owned backend modules in `app/backend/api/`,
`app/backend/services/`, and `app/backend/cruds/`. `site sync` mirrors them to
the corresponding custom packages under `generated/backend/app/`:

```text
generated/backend/app/
├── api/endpoints/custom/
├── services/custom/
└── cruds/custom/
```

Every module under `app/backend/api/` that directly defines a top-level
`router` is included automatically. Define its prefix and tags on the router;
no additional OneSite configuration is required:

```python
from fastapi import APIRouter

from app.services.custom.health import get_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return get_health()
```

Nested API packages are supported. Helper modules without a top-level `router`
are copied but are not registered. Removing a source file removes its mirrored
custom copy on the next sync. Import custom services and CRUDs through
`app.services.custom.*` and `app.cruds.custom.*`.

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

    @classmethod
    async def on_after_bulk_delete(cls, session, olds, context):
        # Called once for the whole batch, before commit.
        pass

    @classmethod
    async def on_after_commit_bulk_delete(cls, olds, context):
        # Called once for the whole batch, after commit.
        pass
```

`on_before_create/update/delete` and `on_after_create/update/delete` run in the same transaction as the CUD operation. The generated service commits only after they succeed and rolls back on any exception. A hook may declare only the named arguments it needs: `session`, `old`, `changes`, or `context`. `context` contains `operation`, `input_data`, and `changed_fields`.

`on_after_commit_create/update/delete` runs after commit; failures are logged and cannot roll back the database. Use a transactional outbox rather than direct email, HTTP or message-broker calls when reliable external delivery is required.

Bulk deletion has two class-level hooks: `on_after_bulk_delete` runs once in
the batch transaction, while `on_after_commit_bulk_delete` runs once after a
successful commit. Both receive `olds`, a list of deleted row snapshots, and
`context.operation` is `"bulk_delete"`. They must be declared with
`@classmethod`. Per-record delete hooks still run for each deleted row. The
batch is atomic and duplicate or missing IDs are ignored.

Background work should be submitted to the application's task system from an
`on_after_commit_*` hook. For reliable external delivery, use a transactional
outbox or another durable queue.

| Hook family | Execution | Can roll back the CUD transaction? |
|---|---|---|
| `on_before/after_create/update/delete` | Same transaction | Yes |
| `on_after_commit_create/update/delete` | Inline, after commit | No |
| `on_after_bulk_delete` | Once per batch, same transaction | Yes |
| `on_after_commit_bulk_delete` | Once per batch, after commit | No |

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

Link tables with only relation keys become multi-select fields; extra fields keep standalone CRUD support. Self-referencing FKs can generate a tree view. A related model can also be rendered as leaf records under each tree node:

```python
from onesite.config import OneSiteConfig, TreeLeafConfig, TreeViewConfig


class AssetFolder(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        tree_view=TreeViewConfig(
            leaf=TreeLeafConfig(
                model="AssetDocument",
                parent_field="folder_id",
                label_field="name",
                page_size=20,
            )
        )
    )


class AssetDocument(SQLModel, table=True):
    folder_id: int = Field(foreign_key="asset_folder.id")
    name: str
```

The tree loads documents lazily when a folder is expanded. Leaf pagination is independent of folder pagination, and standalone leaf models link to their detail pages.

## `__onesite__` model configuration

Place model-level options in `__onesite__` (or table `info.site_props`). Key options include:

For editor autocomplete and validation, `__onesite__` also accepts the typed
Pydantic configuration. The dictionary form remains fully supported:

```python
from onesite.config import ImportExportConfig, ListMode, OneSiteConfig

class Product(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        icon="Package",
        permissions={"user": "r", "admin": "crud", "developer": "crud"},
        edit_mode="drawer",
        list_mode=ListMode.GRID,
        import_key="sku",
        importable=ImportExportConfig(fields=["sku", "name"]),
    )
```

| Option | Effect |
| --- | --- |
| `translations` | Model, field and enum labels for `zh`/`en`. |
| `icon` | Lucide icon name for navigation. |
| `permissions` | Model CRUD permissions by role. |
| `visible` | Navigation visibility by role. |
| `owner_field` | User-owned resource filtering, e.g. `"owner_id"`. |
| `is_link_table` | Marks a many-to-many link table. |
| `tree_view` | Enables a self-referencing tree; an object may configure a related `leaf` model. |
| `is_singleton` | Creates a single configuration-like record UI/API. |
| `frontend_only` | Excludes a model from backend persistence. |
| `page_edit` | Legacy boolean for full-page create/edit; equivalent to `edit_mode: "page"`. |
| `edit_mode` | Create/edit container: `"modal"` (default), `"page"`, or right-side `"drawer"`. |
| `list_mode` | Collection layout: `"list"` (default table) or responsive card `"grid"`. |
| `actions` | Adds permission-controlled custom action buttons. |
| `ui.detail.layout` | Shared layout for detail views and create/edit fields. |
| `importable` / `exportable` | Enables CSV import/export flows. |
| `import_key` | Field used for import upsert matching. |

For a right-side sliding create/edit form:

```python
__onesite__ = {"edit_mode": "drawer"}
```

For a responsive card grid instead of the default table:

```python
__onesite__ = {"list_mode": "grid"}
```

### Detail page layout

Use `ui.detail.layout` to arrange both the read-only detail view and generated
create/edit fields. A string is a field, an array is a horizontal row, and an
object with `section`, `title` and `items` is a titled card. Sections can share
a row; `span` controls their relative width (from 1 to 4). On small screens all
rows stack vertically.

```python
__onesite__ = {
    "ui": {
        "detail": {
            "layout": [
                {
                    "section": "basic",
                    "title": "基本信息",
                    "items": [["title", "protocol"], "endpoint"],
                },
                [
                    {
                        "section": "connection",
                        "title": "连接设置",
                        "span": 1,
                        "items": ["is_enabled"],
                    },
                    {
                        "section": "auth",
                        "title": "鉴权设置",
                        "span": 2,
                        "items": [["auth_type", "auth_config"]],
                    },
                ],
            ],
        },
    },
}
```

Configured fields must be readable fields and may appear once. Fields
omitted from the layout are appended after the configured content in model
declaration order, so a layout cannot accidentally hide data. FK relationship
cards and JSON collection tabs keep their existing detail-page treatment.

Writable fields that do not belong in a read-only detail view are appended to
the generated editor. JSON submodels use the same `detail.layout` declaration
for both their read-only renderer and structured editor:

```python
class AuthConfig(BaseModel):
    __onesite__ = {
        "ui": {
            "detail": {"layout": [["client_id", "client_secret"], "enabled"]},
        }
    }
    client_id: str = ""
    client_secret: str = ""
    enabled: bool = True
```

Structured JSON child fields can be shown, required, or cleared conditionally.
Controller names normally refer to sibling JSON fields; use `$root.<field>` to
refer to a field on the containing SQLModel record:

```python
def only_for(kind: str):
    return {"info": {"site_props": {
        "visible_when": {"$root.type": [kind]},
        "clear_when_hidden": True,
    }}}

class Properties(SQLModel):
    a: str | None = Field(default=None, sa_column_kwargs=only_for("none"))
    b: str | None = Field(default=None, sa_column_kwargs=only_for("none"))
    c: str | None = Field(default=None, sa_column_kwargs=only_for("password"))
    d: str | None = Field(default=None, sa_column_kwargs=only_for("password"))

class Connector(SQLModel, table=True):
    type: str
    properties: Properties = Field(sa_column=Column(JSON))
```

Add `required_when` with the same condition when a visible child must be
present. Generated create/edit/detail UIs apply the rule immediately, and API
schemas repeat the cleanup and required-field checks. A `$root` reference must
name a field on the containing model.

### Enable / disable actions

For a boolean field, use the `toggle` shorthand instead of defining separate
enable and disable actions. It creates one permission-controlled action, safely
inverts the field on the server, and labels the button **Enable/Disable** (or
**启用/停用**) from the current value.

```python
class User(SQLModel, table=True):
    __onesite__ = {
        "actions": {
            "toggle_enabled": {"toggle": "enabled", "permissions": "da"},
        },
    }
    enabled: bool = True
```

The shorthand may include other fields to update, but do not set `data` for the
toggle field itself.

### Function-based actions

Use `@action` when an operation needs arbitrary Python business logic. The
method runs on the tracked SQLModel object in one database transaction; it may
request `context`, `session`, or `current_user` as named arguments.

```python
from onesite_runtime import ActionContext, ActionState, action

class Dataset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str = "draft"
    is_enabled: bool = False

    @action(permissions="da", label="Toggle", unavailable="disable")
    def toggle_enabled(self, *, context: ActionContext):
        self.is_enabled = not self.is_enabled

    @toggle_enabled.available
    async def can_toggle_enabled(self, *, session, current_user):
        if self.status != "draft":
            return ActionState(
                visible=True,
                enabled=False,
                reason="Only draft datasets can be changed",
            )
        return True
```

An availability method may return `bool`, `None`, or `ActionState`. Dynamic
availability is evaluated on the server and loaded by list/detail pages in a
single batched request. It is checked again when the action is executed, so UI
visibility is never the authorization boundary. Use `unavailable="hide"`
(default) to hide a false boolean result or `"disable"` to keep a disabled
button visible. Availability methods may run repeatedly and should not mutate
data or trigger external side effects.

For a condition that only reads fields already present in the row, the compact
declarative form avoids the extra state request and is checked in both the
frontend and backend:

```python
@action(condition={"field": "status", "op": "eq", "value": "draft"})
def publish(self):
    self.status = "published"
```

Do not combine `condition=` with `@method.available`. Existing configured
actions, including `toggle` plus `condition`, remain supported.

CSV import/export can also use an object configuration. M2M relations are
included only when explicitly listed; their values use `;` as the separator.
Related objects must already exist when importing.

```python
__onesite__ = {
    "import_key": "sku",
    "exportable": {
        "fields": ["sku", "name", "category_id"],
        "foreign_keys": {"category_id": "title"},
        "m2m": {"tags": "title"},
    },
    "importable": {
        "fields": ["sku", "name", "category_id"],
        "foreign_keys": {"category_id": "title"},
        "m2m": {"tags": "title"},
    },
}
```

The example exports `category_id` as `Category.title` and `tags` as
`tag one;tag two`. Import performs the reverse lookup. A matching `import_key`
updates the existing row; otherwise a new row is created. Set field-level
`site_props` `importable=False` or `exportable=False` to exclude a field even
when it appears in a model-level field list.

When imports, exports, dashboard tools, or scheduled tasks are configured,
`site sync` also generates a unified **Task Center** page. It lists imports,
exports, tool executions, and scheduled-task executions submitted to the
in-process task queue, with kind/name/status filters, progress, timestamps,
results, errors, and downloadable outputs. User-started work is scoped to the
signed-in user; scheduled executions are visible according to each task's
manual permissions. The page continues to work after a browser refresh or a
missed WebSocket message. Completed and failed executions, along with their
managed uploads and downloadable outputs, are retained for 24 hours. Cleanup
runs at application startup and every five minutes. The
legacy synchronous CSV import API remains available by omitting
`background=true`. Both paths require model-level create and update
permissions. Standard CSV imports also enforce the caller's field permissions
per create/update row and force the configured owner scope for non-admin users.

> **TODO (optimization):** Standard CSV imports currently use the regular
> create/update service path, so transactional and post-commit model hooks run
> once per imported row. Add a batch-oriented import path that reduces
> per-row commits and hook overhead while preserving validation, rollback
> semantics, and reliable post-commit processing.

Hide selected executions from both the Task Center list and detail API with an
exact `kind` plus `name` pair. Hidden jobs still execute, persist, notify, and
follow the same 24-hour retention policy.

```python
from onesite.config import HiddenTask, SiteConfig, TaskCenterConfig

config = SiteConfig(
    task_center=TaskCenterConfig(hidden=[
        HiddenTask(kind="tool", name="internal_cleanup"),
        HiddenTask(kind="scheduled_task", name="heartbeat"),
        HiddenTask(kind="import", name="audit_log"),
        HiddenTask(kind="export", name="audit_log"),
    ]),
)
```

| `refresh_interval` | Enables periodic list refresh. |
| `visualize` | Legacy model-level chart configuration; use project-level `visualizations.py` for new charts. |
| `dashboard_metrics` | Legacy model-level Dashboard KPI configuration; use project-level `visualizations.py` for new KPIs. |
| `is_notification_table` | Enables notification-center behavior and realtime push. |
| `time_series_table` | Configures TimescaleDB/time-series generation. |

### Custom import/export

For non-CSV workflows, set `custom: True` on either configuration. `site sync`
creates `app/custom_io/<model_module>.py` once and synchronizes it to
`generated/backend/app/custom_io/` on every sync. Custom operations always run
in the background; OneSite saves uploads, queues work, publishes completion
notifications, and exposes export downloads automatically.

```python
__onesite__ = {
    "importable": {"custom": True},
    "exportable": {"custom": True},
}
```

Implement the generated hooks as follows:

```python
from pathlib import Path
from typing import Any

async def import_product(file: Path, context=None) -> dict[str, Any]:
    if context:
        await context.set_progress(50, "Parsing workbook")
    # Return at least success, failed, and errors.
    return {"success": 10, "failed": 0, "errors": []}

async def export_product(filters: dict[str, Any], context=None) -> Path:
    if context:
        await context.set_progress(50, "Writing workbook")
    # Create a file and return its existing path.
    return Path("/tmp/products.xlsx")
```

Custom imports do not need `import_key`. The export hook receives the active
list filters and may produce any file type; OneSite copies it to the export
directory and notifies the requesting user when it is ready. The optional
`context` parameter is backwards compatible; call `await context.set_progress`
with a value from 0 to 100 to expose custom stages on the task page. Custom
import code is responsible for content-level authorization because OneSite
cannot interpret an arbitrary file format. Use `context.current_role` to apply
field permissions and `context.scoped_owner_id` to force or validate ownership;
the generated endpoint still requires both model-level create and update
permission before a custom import is queued.

Useful field-level `site_props` are `permissions`, `is_search_field`, `component`, `create_optional`, `update_optional`, `is_foreign_key`, `reverse_display`, `allow_download`, `group`, `fixed_keys` and `lock_keys`.

Project-level charts and Dashboard KPIs are declared independently from SQLModel
classes:

```python
from onesite.visualization import (
    chart, count, dashboard_metric, dim, line, metric, pie,
)

visualizations = [
    chart(
        "daily_sales", title="Daily sales", preset=line.smooth, model="Order",
        x=dim("created_at", bucket="day"),
        y=metric("amount", aggregate="sum"),
    ),
    chart(
        "orders_by_status", title="Orders by status",
        preset=pie.rounded_donut, model="Order",
        category=dim("status"), value=count(),
    ),
]

dashboard_metrics = [
    dashboard_metric(
        "order_count", model="Order", title="Orders",
        aggregation="count",
        where={"created_at": {"period": "today"}},
        icon="ShoppingCart", color="blue", order=1,
    ),
    dashboard_metric(
        "paid_over_total", model="Order", title="Paid / total orders",
        items=[
            {"aggregation": "count", "where": {"status": "paid"}},
            {"aggregation": "count"},
        ],
        separator=" / ", icon="ReceiptText", color="purple", order=2,
    ),
]
```

Preset constants are grouped by chart type for editor completion, such as
`line.smooth`, `line.stacked_area_gradient`, and `pie.rounded_donut`. Existing
string presets remain supported.

OneSite validates each preset's semantic inputs and generates a shared query API
plus an ECharts dashboard runtime. Related fields can use paths such as
`category.name`. See `docs/visualization-redesign.md` for the contracts and
migration design. KPIs keep using their source model's generated endpoint, so
the existing field validation and role-permission checks still apply. The old
`__onesite__.dashboard_metrics` configuration remains temporarily compatible
and emits a deprecation warning during `site sync`. KPI time windows use the
same relative-time `where` form as charts; the older `time_field` + `period`
pair remains temporarily compatible. A KPI can combine two or more `items` in
one card, with one title and icon; set `separator` to display forms such as
`" / "`, `" − "`, or `" | "`. Each item uses its own aggregation, field,
filter, and number format.

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
- EN/ZH locale generation and three structural themes
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

The tag is applied to both `<project>-backend` and `<project>-frontend`. `site build` writes `deploy/docker-compose.yml`. `site create`, `site init`, and `site sync` ensure that `deploy/.env.example` exists; copy it to `deploy/.env` for deployment-specific overrides. `site compose` automatically passes that `.env` file when present. PostgreSQL is included when `database_url` starts with `postgresql`; configure production credentials and API origins before exposing the application.

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
├── site_config.py
├── app/                       # developer-owned source
│   ├── models/                # SQLModel source of truth
│   ├── integrations/
│   │   └── mqtt/              # MQTT handler implementations
│   ├── tools/                  # Dashboard tool implementations
│   ├── tasks/                  # scheduled task implementations
│   ├── frontend/
│   │   ├── features/           # custom frontend feature source
│   │   └── shared/             # shared custom frontend modules
│   ├── backend/                # custom backend source
│   │   ├── api/                # auto-registered APIRouter modules
│   │   ├── services/
│   │   └── cruds/
│   └── utils/                  # reusable developer-owned backend helpers
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
│           ├── components/
│           └── custom/         # mirrored developer-owned frontend source
├── deploy/
│   ├── .env.example
│   ├── .env                   # optional, developer-created and gitignored
│   └── docker-compose.yml     # generated by site build
```

See the [design principles](docs/design-principles.md) and `examples/` for end-to-end model examples, including permissions and IoT/time-series scenarios.

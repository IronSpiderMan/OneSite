# OneSite

OneSite is a powerful model-driven CLI tool that automatically generates a full-stack web application (FastAPI + React/Vite) from simple Python SQLModel definitions.

It automates the repetitive work of building CRUD APIs, database schemas, and frontend management pages, allowing you to focus on business logic.

## Features

- **Full-Stack Generation**: Generates Backend (FastAPI, SQLModel, Pydantic) and Frontend (React, Tailwind, Zustand, Lucide Icons).
- **Model-Driven**: Define your data models in standard Python code, and let OneSite handle the rest.
- **Auto CRUD & Validation**: Automatically generates Create, Read, Update, Delete APIs and UI, including unique constraints validation.
- **Search & Filters**: Mark fields as searchable to generate list-page filters (bool/enum/string contains/datetime range). Each `is_search_field` appears as an individual filter input.
- **Smart Foreign Key Display**: List pages automatically display the related record's label field (first `unique + is_search_field` field from the target model) instead of raw IDs.
- **Smart UI Components**:
  - `bool` -> **Switch** / **Badge**
  - `Enum` -> **Select** / **Badge**
  - `datetime` -> **Text**
  - **Image Upload**: Detects image fields (e.g. `avatar`, `_image`) and generates file upload and preview components.
  - **File Attachment**: Detects file fields (e.g. `report_file`, `_file` suffix) and generates file upload components with built-in preview.
    - **Preview Support**: PDF, Word (docx), Excel (xlsx, csv), Markdown, Code/Text, Video, Audio, Images.
  - **Foreign Key**: Auto-detects foreign keys and generates searchable select dropdowns (`SearchableSelect`).
    - **Label Field**: SearchableSelect uses the first field marked as both `unique=True` and `is_search_field=True` from the target model for searching and display.
    - **List Page Display**: FK columns show the resolved label (e.g., username, book title) instead of raw IDs.
  - **Many-to-Many**: Supports M2M relationships via link tables, generating multi-select components.
  - **One-to-Many (Reverse FK)**: Displays related items in a paginated list on the detail page (e.g. Products under a Category). Configurable.
- **Better UX Defaults**: Delete confirmation dialogs; toast notifications for create/update.
- **Pagination**: Built-in standard pagination support for all list views.
- **Auto Refresh**: Configurable auto-refresh for real-time data monitoring.
- **Dashboard**: Auto-generated dashboard page with statistics cards, charts (bar, line, pie), and scheduled tasks management.
- **Scheduled Tasks**: Cron and interval tasks with APScheduler, displayed on Dashboard with enable/disable/edit/run controls and toast notifications.
- **Bulk Delete**: Select multiple items in list pages for batch deletion.
- **Test Generation**: Auto-generated pytest tests for backend APIs and Vitest tests for frontend services/stores.
- **Authentication & Security**:
  - **Built-in Login**: Modern login page with JWT authentication.
  - **Protected Routes**: Automatic auth guards for frontend pages.
  - **Secure APIs**: CRUD endpoints default to authenticated access; static files are public.
  - **User Management**: Secure password hashing and role-based field access.
- **Containerization**: Built-in support for Docker/Podman build and Compose.

## Installation

You can install OneSite directly from PyPI:

```bash
pip install onesite
```

*(Optional) If you want to install from source:*
```bash
git clone https://github.com/IronSpiderMan/OneSite.git
cd OneSite
pip install -e .
```

## Quick Start

### 1. Create or Initialize a Project

You have two options:

**Option A: Create a new project from scratch**
```bash
site create myproject
cd myproject
```

**Option B: Initialize an existing project**
If you already have a directory with existing models or backend/frontend structure:
```bash
cd existing_project
site init
```
This creates `site_config.json` and `models/` with base models (User, SystemConfig, CustomConfig) if they don't exist.

This creates a new directory structure:
```
myproject/
├── backend/    # FastAPI Backend
├── frontend/   # React Frontend
└── models/     # Your Data Models (Source of Truth)
```

### 2. Define Your Models

Add your models to the `models/` directory.

#### Basic Model
`models/product.py`:
```python
from typing import Optional
from sqlmodel import Field, SQLModel
from enum import Enum

class Category(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    is_active: bool = True
    category: Category = Category.ELECTRONICS
    # Image field (auto-detected by name 'image', 'avatar', or '_image' suffix)
    image: Optional[str] = Field(default=None, sa_column_kwargs={"info": {"site_props": {"component": "image"}}})
```

#### File Attachments
`models/document.py`:
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    
    # Method 1: Auto-detection via '_file' suffix
    report_file: Optional[str] = Field(default=None)
    
    # Method 2: Explicit component definition
    attachment: Optional[str] = Field(default=None, sa_column_kwargs={"info": {"site_props": {"component": "file"}}})
    
    # Method 3: Disable download (preview only)
    preview_only: Optional[str] = Field(default=None, sa_column_kwargs={"info": {"site_props": {"component": "file", "allow_download": False}}})
```

#### Foreign Key Relationship
`models/post.py`:
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    
    # Foreign Key to User
    # Configure reverse display on the field itself
    # reverse_display: Controls whether this relationship is shown on the target model's detail page (e.g. User page)
    # Default is True.
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", sa_column_kwargs={"info": {"site_props": {"reverse_display": True}}})
```

#### Table Names (`__tablename__`)
SQLModel's default table name is not snake_case. By default it uses the lowercased class name.
For example, `DataModel` becomes `datamodel` (not `data_model`).

OneSite enforces snake_case table names for `table=True` models during code generation and at backend startup.
This keeps table names consistent with OneSite's generated module/page names and makes `foreign_key="data_model.id"` work as expected.

If you want to override the table name, set `__tablename__` explicitly:

```python
class DataModel(SQLModel, table=True):
    __tablename__ = "data_model"
    id: Optional[int] = Field(default=None, primary_key=True)
```

#### Internationalization (i18n)
OneSite generates `frontend/src/locales/en.json` and `frontend/src/locales/zh.json` during `site sync`.
Pages, menus, buttons, and model/field labels use these keys (via i18next).

##### Model & Field Labels
You can provide translations at model level using `__onesite__`.

```python
class DataSource(SQLModel, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "数据源",
                "fields": {
                    "name": "数据源名称",
                    "type": "数据源类型",
                },
            },
            "en": {
                "name": "Data Source",
                "fields": {
                    "name": "Name",
                    "type": "Type",
                },
            },
        }
    }
```

- `translations.<lang>.name`: model display name (used in menu/page titles)
- `translations.<lang>.fields.<field>`: field label (used in list headers and forms)

If you don't provide translations, OneSite falls back to auto-generated labels (e.g. `full_name` -> `Full Name`).

##### Common UI Text
General UI strings (e.g. Settings page, confirm dialogs, toast messages, filter panel labels) are generated into `common.*`, `settings.*`, `toast.*`, `alert.*`.

#### Many-to-Many Relationship
To define a Many-to-Many relationship (e.g., Posts have many Tags), create a link table model with specific metadata.

`models/tag.py`:
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
```

`models/post_tag_link.py`:
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class PostTagLink(SQLModel, table=True):
    # Required metadata to identify this as a M2M link table
    __onesite__ = {"is_link_table": True}
    
    post_id: Optional[int] = Field(default=None, foreign_key="post.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
```
OneSite will automatically inject a `tag_ids` field into the `Post` form, allowing you to select multiple Tags.

Notes:
- Link tables are treated as relationship carriers by default and are not exposed as standalone pages/menus.
- If a link table contains extra non-FK fields (association table), OneSite will generate standalone CRUD pages/endpoints for it so you can edit those extra fields. You can hide it from frontend menu/routes via `__onesite__ = {"show_in_menu": False}`.
- Selection UI for both Foreign Keys and M2M uses `SearchableSelect`, which queries the target model list endpoint with filters on the target's label field (first `unique + is_search_field` field).
- OneSite generates relationship endpoints like:
  - `GET /posts/{id}/tags` (targets related to a source item)
  - `GET /tags/{id}/posts` (reverse M2M: sources related to a target item)

##### Ordering (Link Field: `order`)
If your link table defines an integer field named `order`, OneSite treats the relationship as ordered:
- The edit form uses a dedicated ordered selector with drag-and-drop to reorder selected items.
- Create/Update writes `order=1..n` based on the submitted `*_ids` array order.
- A meta endpoint is generated to fetch the current order:
  - `GET /posts/{id}/tags_with_meta` -> `[{id, label, order}]`

If the link table does not have an `order` field, OneSite treats the relationship as unordered.

##### Direction (Owner Side)
By default, OneSite injects the M2M `*_ids` field only on the "source" side of the link table.
If you need to control which side can edit the relationship, you can configure it explicitly:

```python
class PostTagLink(SQLModel, table=True):
    __onesite__ = {
        "is_link_table": True,
        "m2m": {
            "directions": [
                {"from": "post", "to": "tag", "editable": True},
                {"from": "tag", "to": "post", "editable": False},
            ]
        },
    }
```

If `m2m.directions` is not provided, OneSite falls back to foreign key field order in the link table:
- the first FK is treated as the source (gets `target_ids` in Create/Update)
- the second FK is treated as the target (gets reverse M2M endpoints and detail-page related list)

Example: `post_id` then `tag_id` means `Post` gets `tag_ids` and `GET /posts/{id}/tags`, while `Tag` gets `GET /tags/{id}/posts`.

#### Model Actions

OneSite allows you to define custom "actions" for your models. An action is a predefined set of field updates that can be triggered from the UI with a single click.

```python
class AlarmStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKED = "ACKED"

class AlarmRecord(SQLModel, table=True):
    __onesite__ = {
        "actions": {
            "ack": {
                "status": "ACKED",
                "user_id": "{{user_id}}" # Automatically resolved to current user ID
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    status: AlarmStatus = AlarmStatus.ACTIVE
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

Generated features:
- **Action Buttons**: OneSite automatically adds buttons for each defined action in the list page table rows.
- **Dynamic Field Updates**: Clicking the button sends a request to a dedicated endpoint (e.g., `POST /api/v1/alarm_records/{id}/actions/ack`) which performs the configured updates.
- **User ID Resolution**: The `{{user_id}}` placeholder is automatically resolved to the ID of the authenticated user performing the action at runtime.
- **Type Safety**: Actions use the model's generated Update schema, ensuring type consistency and validation.

#### CSV Import & Export

OneSite can generate CSV import and export functionality for your models. Simply add `importable` and/or `exportable` to your model's `__onesite__` configuration:

```python
class Product(SQLModel, table=True):
    __onesite__ = {
        "importable": True,  # Enable CSV import
        "exportable": True,  # Enable CSV export
        "import_key": "name",  # Unique field for upsert (required if no title with unique=True)
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)  # unique=True makes this the default import_key
    price: float
    quantity: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Import Key Configuration**:
- Set `import_key` in `__onesite__` to specify which field identifies unique records
- If `import_key` is not set, defaults to `title` if it has `unique=True`
- If neither is configured, `site sync` will error out

Generated features:
- **Export Button**: Downloads all records as a CSV file directly.
- **Import Button**: Opens a file picker to upload a CSV file. The import runs synchronously and shows results (created/updated/failed count) when complete.
- **Template Download**: If only `importable` is enabled (without `exportable`), a template download button is provided showing the expected CSV format.

**CSV Format**:
- The first row contains field names (excluding `id`)
- Each subsequent row represents one record
- Boolean values should be `true`/`false`
- Empty cells are treated as `None`/`null`
- **Foreign Key Fields**: Use the label field value (e.g., author name, username) instead of IDs. The label field is the first `unique + is_search_field` field from the target model.

**Import Behavior (Upsert)**:
- Import uses **upsert logic**: if a record with the same `import_key` value exists, it updates that record; otherwise creates a new one
- `created_at`: Always ignored during import, auto-set to current time on create
- `updated_at`: Auto-updated to current time on every create and update
- Enum values should be the actual string value (e.g., `SUCCEED`, not `NotificationStatus.SUCCEED`)
- **Foreign Key Resolution**: FK fields in CSV use labels (e.g., author name). OneSite resolves them to IDs automatically:
  - First, checks a pre-built cache of all FK target records
  - If not found, performs a database lookup by the label field
  - Falls back to accepting numeric IDs for backward compatibility
  - Raises an error if the label/ID cannot be resolved
- Returns detailed statistics: `{success, failed, created, updated, errors}`

**Export Encoding**:
- All exports use UTF-8 with BOM for Excel compatibility
- **Foreign Key Fields**: Exported as human-readable labels (e.g., author name, username) instead of raw IDs, making CSV files more readable and easier to edit manually

#### Dashboard & Visualization
OneSite can generate a dashboard page with statistics and charts. Configure `visualize` in your model's `__onesite__`:

```python
from enum import Enum

class NotificationStatus(str, Enum):
    SUCCEED = "SUCCEED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"

class NotificationRecord(SQLModel, table=True):
    __onesite__ = {
        "visualize": {
            "show": True,                    # Show on dashboard
            "chart_type": "bar",             # bar, line, pie
            "label_field": "status",         # Field to group by
            "value_field": "id",             # Field to aggregate
            "aggregation": "count",           # sum, count, avg, min, max
            # "time_field": "created_at",     # Optional: for time-based line charts
            "title": "通知统计",             # Optional custom title
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    status: NotificationStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Chart Types**:
- `bar`: Bar chart for categorical data (grouped by `label_field`)
- `pie`: Pie chart for percentage distribution
- `line`: Line chart for time-series trends (requires `time_field`)

**Time-Based Charts** (line chart):
- Set `chart_type: "line"` and provide `time_field` (e.g., `created_at`)
- Supports `period` parameter: `day`, `week`, `month`

**Generated Features**:
- Backend: `GET /{module_name}/stats` endpoint returns `{labels: [], values: [], title: "..."}`
- Frontend: Dashboard page with Recharts visualizations
- Auto-detects all models with `visualize.show: True`

#### Scheduled Tasks
OneSite supports scheduled tasks (cron and interval) displayed on the Dashboard page. Configure `scheduled_tasks` in `site_config.json`:

```json
{
  "scheduled_tasks": [
    {
      "name": "daily_summary",
      "func": "app.tasks.alarm:daily_summary",
      "cron": "0 8 * * *",
      "description": "每天早上8点发送告警汇总",
      "enabled": true
    },
    {
      "name": "health_check",
      "func": "app.tasks.alarm:health_check",
      "interval": 300,
      "description": "每5分钟检查系统健康状态",
      "enabled": true
    }
  ]
}
```

**Task Types**:
- **Cron Task**: Set `cron` field with standard cron expression (e.g., `0 8 * * *` = daily at 8:00)
- **Interval Task**: Set `interval` field with seconds (e.g., `300` = every 5 minutes)

**Generated Features**:
- **Backend**: APScheduler with AsyncIOScheduler manages task execution
- **Memory-Only Registry**: Task state is lost on restart (enabled/disabled status resets)
- **Frontend Dashboard**: View all tasks, enable/disable, edit cron/interval, manually trigger
- **Task Files**: Generated in `backend/app/tasks/{module}.py` (not overwritten if exists)
  - Example: `app.tasks.alarm:daily_summary` -> `backend/app/tasks/alarm.py`
  - Functions include `# TODO: 实现业务逻辑` placeholder for user implementation

**Task Configuration Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique task identifier |
| `func` | string | Module path and function: `app.tasks.alarm:daily_summary` |
| `cron` | string | Cron expression (used if `interval` is 0 or omitted) |
| `interval` | int | Interval in seconds (takes precedence over `cron` if > 0) |
| `description` | string | Task description shown in UI |
| `enabled` | bool | Whether task starts enabled on app startup |

**Frontend API Endpoints**:
- `GET /tasks/` - List all tasks
- `GET /tasks/{name}` - Get single task
- `POST /tasks/{name}/run` - Manually trigger task
- `POST /tasks/{name}/enable` - Enable task
- `POST /tasks/{name}/disable` - Disable task
- `PUT /tasks/{name}` - Update cron/interval/description

**Dashboard UI Features**:
- Toast notifications for all task operations (run, enable, disable, update)
- Local time display for next_run (no timezone suffix)
- Running spinner on run button during execution
- Cron/Interval switch in edit modal

#### Bulk Delete
List pages include multi-select checkboxes for batch operations. Selecting items reveals a bulk delete button:

```
[ ] Name        | Status
[x] Item 1      | Active
[x] Item 2      | Inactive
[x] Item 3      | Active

[Delete (3)] [Create Product]
```

- Click the checkbox in the table header to select/deselect all visible items
- Bulk delete requires confirmation before executing
- Both single and bulk delete are available for all non-singleton models

#### Test Generation
OneSite auto-generates test files during `site sync`:

**Backend Tests** (`backend/tests/test_{module_name}_api.py`):
```python
# pytest + httpx AsyncClient
class TestNotificationRecordAPI:
    async def test_list_notification_records(self, client):
        response = await client.get("/notification_records/")
        assert response.status_code == 200

    async def test_create_notification_record(self, client):
        payload = {"status": "SUCCEED"}
        response = await client.post("/notification_records/", json=payload)
        assert response.status_code == 200
```

**Frontend Tests** (`frontend/src/{module_name}.test.ts`):
```typescript
// Vitest + mocking
describe('NotificationRecord Service', () => {
    it('getNotificationRecords returns paginated response', async () => {
        const result = await getNotificationRecords(1, 20);
        expect(result.items).toHaveLength(1);
    });
});
```

Run tests:
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

#### Configuration Models (Settings Page)
OneSite reserves two special models for the unified `/settings` page:
- `SystemConfig` in `models/system_config.py`: server-persisted system settings, admin-only
- `CustomConfig` in `models/custom_config.py`: browser-persisted user preferences (localStorage), available to all users

#### Navigation Order
You can control the sidebar menu order via `site_config.json`:

```json
{
  "nav_order": ["user", "group", "product", "tag"]
}
```

Items not listed in `nav_order` will be appended after the listed ones.

#### Global Resources (Redis, RabbitMQ & MQTT)

OneSite can automatically generate initialization code for global resources like Redis, RabbitMQ and MQTT if configured in `site_config.json`.

```json
{
  "redis": {
    "url": "redis://localhost:6379/0",
    "password": "optional_password"
  },
  "rabbitmq": {
    "url": "amqp://guest:guest@localhost:5672/"
  },
  "mqtt": {
    "url": "mqtt://localhost:1883",
    "username": "admin",
    "password": "public",
    "callbacks": [
      {"topic": "device/+/data", "handler": "on_device_data"}
    ]
  }
}
```

Generated features:
- **Automatic Client Initialization**: Generates `app/core/redis.py`, `app/core/rabbitmq.py` and `app/core/mqtt.py` with pre-configured clients.
- **Lifecycle Management**: RabbitMQ and MQTT connections are automatically established on startup and closed on shutdown in the FastAPI lifespan.
- **Environment Integration**: Configuration is automatically synced to the backend `.env` file.
- **Dependency Management**: Automatically adds `redis`, `aio-pika` and `gmqtt` to the generated `requirements.txt`.

Usage in your code:
```python
from app.core.redis import redis_client
from app.core.rabbitmq import rabbitmq_manager
from app.core.mqtt import mqtt_manager

# Redis (Async)
await redis_client.set("key", "value")

# RabbitMQ (aio-pika)
async with rabbitmq_manager.channel.transaction():
    await rabbitmq_manager.channel.default_exchange.publish(...)

# MQTT
await mqtt_manager.publish("topic", {"key": "value"})
```

##### RabbitMQ Consumers (Callbacks)

If you have RabbitMQ enabled, OneSite provides a standard way to handle message callbacks (consumers):

1.  **Define your consumer**: Add a file in `backend/app/consumers/` (e.g., `my_consumer.py`).
2.  **Register the callback**: Use `rabbitmq_manager.register_consumer` to link a queue to your async function.

Example `app/consumers/my_consumer.py`:
```python
import aio_pika
from app.core.rabbitmq import rabbitmq_manager

async def on_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        print(f"Received message: {message.body}")

# Register it for the 'my_queue'
if rabbitmq_manager:
    rabbitmq_manager.register_consumer("my_queue", on_message)
```

3.  **Import your consumer**: Make sure your consumer file is imported in `backend/app/consumers/__init__.py`. OneSite automatically imports this directory on startup to start all registered consumers.

#### MQTT (EMQX)

OneSite can automatically generate MQTT client initialization code and message handlers if configured in `site_config.json`.

```json
{
  "mqtt": {
    "url": "mqtt://localhost:1883",
    "username": "admin",
    "password": "public",
    "client_id": "onesite_backend",
    "callbacks": [
      {"topic": "device/+/data", "handler": "on_device_data"},
      {"topic": "alarm/#", "handler": "on_alarm"}
    ]
  }
}
```

**Configuration Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `url` | string | MQTT broker URL (e.g., `mqtt://localhost:1883`) |
| `username` | string | Optional username for authentication |
| `password` | string | Optional password for authentication |
| `client_id` | string | MQTT client identifier |
| `callbacks` | array | List of message callbacks to generate |

**Callback Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `topic` | string | MQTT topic pattern (supports wildcards `+` and `#`) |
| `handler` | string | Handler function name (used as filename and function name) |

Generated features:
- **Automatic Client Initialization**: Generates `app/core/mqtt.py` with pre-configured `mqtt_manager`.
- **Callback Files**: Generates `app/consumers/mqtt/<handler>.py` for each callback.
- **Handler Registration**: Automatically imports callbacks module to register handlers before connecting.
- **Lifecycle Management**: MQTT connection is automatically established on startup and closed on shutdown in the FastAPI lifespan.
- **Environment Integration**: Configuration is automatically synced to the backend `.env` file.
- **Dependency Management**: Automatically adds `gmqtt` to the generated `requirements.txt`.

##### MQTT Callback Implementation

OneSite generates a callback file for each configured handler. Example for `on_device_data`:

Generated file `app/consumers/mqtt/on_device_data.py`:
```python
# MQTT callback for topic: device/+/data
from app.core.mqtt import mqtt_manager

async def on_device_data(topic: str, payload: str):
    """
    MQTT message callback for topic: device/+/data

    Args:
        topic: MQTT topic
        payload: Message payload (usually JSON string)
    """
    # TODO: Implement your business logic here
    pass

# Register handler
if mqtt_manager:
    mqtt_manager.register_handler("device/+/data", on_device_data)
```

**Important**: OneSite will NOT overwrite the callback file if the handler function already exists. This allows you to implement your business logic without losing changes on subsequent `site sync` runs.

##### MQTT Manager API

`mqtt_manager` provides the following methods:

| Method | Description |
|--------|-------------|
| `register_handler(topic, callback, qos=1)` | Register a message handler for a topic pattern |
| `subscribe(topic, qos=1)` | Subscribe to a topic (async) |
| `unsubscribe(topic)` | Unsubscribe from a topic (async) |
| `publish(topic, payload, qos=1, retain=False)` | Publish a message to a topic (async) |
| `disconnect()` | Gracefully disconnect from the broker (async) |

**Topic Wildcards**:
- `+` matches a single level (e.g., `device/+/data` matches `device/001/data`)
- `#` matches multiple levels (e.g., `sensor/#` matches `sensor/temperature/room1`)

**on_message callback parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `topic` | str | Message topic |
| `payload` | str | Message content (decoded from bytes) |
| `qos` | int | Quality of Service level (0, 1, 2) |

#### Notifications (Optional)
OneSite can generate a notification center if you provide a `Notification` model and mark it as the notification table:

```python
class Notification(SQLModel, table=True):
    __onesite__ = {
        "is_notification_table": True,
        "permissions": {
            "user": "rcu",    # All users can access via API
            "admin": "rcu",
            "developer": "rcu",
        },
        "visible": {
            "user": False,     # Not visible in menu
            "admin": True,
            "developer": True,
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

Required fields (names are fixed): `title`, `summary`, `content`, `created_at`, `is_read`, `user_id`.

**Note**: The Notification model does **not** have an `updated_at` field - it uses `is_read` for tracking read status only.

Generated features:
- **Unified WebSocket Infrastructure**: Generates a central `ConnectionManager` (`app/core/ws.py`) and a unified endpoint `/api/v1/ws` for all real-time communications.
- **Header Notification Bell**: Real-time unread badge, infinite-scroll inbox list, and detailed message view.
- **Service-Level Real-time Push**: The backend Service layer automatically triggers WebSocket pushes whenever a notification is created or its read status changes.
- **Frontend Resiliency**: Built-in exponential backoff reconnection logic ensures the notification connection remains active.
- **Admin Send API**:
  - `POST /api/v1/notifications/send` with `{title, summary?, content, user_id? , broadcast?}`
  - `broadcast=true` sends to all active users.

The Settings page uses a top-to-bottom layout:
```
[Save System Config]
system field 1
system field 2
...
[Save Custom Config]
custom field 1
custom field 2
...
```

`models/system_config.py` (Default generated):
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class SystemConfig(SQLModel, table=True):
    __onesite__ = {"config_role": "system", "permissions": "developer-rcu", "is_singleton": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    # Server-side settings
    site_name: str = Field(default="OneSite Admin")
    allow_registration: bool = Field(default=True)
```

`models/custom_config.py` (Default generated):
```python
from enum import Enum
from sqlmodel import Field, SQLModel

class LanguageEnum(str, Enum):
    EN = "en"
    ZH = "zh"

class TimezoneEnum(str, Enum):
    UTC = "UTC"
    ASIA_SHANGHAI = "Asia/Shanghai"

class ThemeEnum(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    IOTHUB = "iothub"

class CustomConfig(SQLModel):
    __onesite__ = {"config_role": "custom", "frontend_only": True}
    
    # Since frontend_only is True, all fields are automatically treated as local storage
    language: LanguageEnum = Field(default=LanguageEnum.EN)
    
    timezone: TimezoneEnum = Field(default=TimezoneEnum.UTC)

    theme: ThemeEnum = Field(default=ThemeEnum.SYSTEM)
```

### 3. Advanced Configuration

You can customize field behavior using `site_props` (recommended via `sa_column_kwargs={"info": {"site_props": {...}}}`).
Note: when you use `sa_column=Column(...)` in SQLModel, you cannot also pass `sa_column_kwargs` (SQLModel limitation). In that case, you can put `site_props` in `schema_extra`/`json_schema_extra`, but support depends on your SQLModel version. The most reliable approach is `sa_column_kwargs.info.site_props`.

#### Field Permissions & Validation
Control field visibility and validation requirements for Create/Update/Export operations.

```python
class User(SQLModel, table=True):
    # ...
    email: str = Field(unique=True) # Unique constraint validation
    password: str = Field(sa_column_kwargs={"info": {"site_props": {
        "permissions": "cu",          # 'c'=Create, 'u'=Update. 'r'=Read (omitted, so password is never sent to frontend)
        "create_optional": False,     # Required when creating a user
        "update_optional": True       # Optional when updating (leave blank to keep current password)
    }}})
```

##### Field Permissions String
A string combining characters to control field behavior:

| Character | Meaning | Description |
|-----------|---------|-------------|
| `r` | Read | Field is included in CSV export |
| `c` | Create | Field is editable in Create form and CSV import |
| `u` | Update | Field is editable in Update form and CSV import |
| `d` | Delete | **Model-level only**, controls delete button visibility |

> **Note**: The `d` (delete) permission is **model-level only**, not field-level. Fields cannot have `d` permission. Delete operations are controlled by the model's `role_permissions`, not individual field permissions.

##### Default Field Permissions

| Field Type | Default | Notes |
|------------|---------|-------|
| Normal fields | `rcu` | Inherit from model config, without `d` (delete is model-level) |
| `id` | `r` | Always read-only |
| `created_at` | `r` | Auto-set on create, never user-provided |
| `updated_at` | `ru` | Auto-updated on every write, readable but not user-settable |

##### Special Fields

OneSite handles these fields with simplified defaults:

| Field | Default Permissions | Auto Behavior |
|-------|-------------------|---------------|
| `id` | `r` | Auto-generated primary key |
| `created_at` | `r` | Auto-set to current UTC time on create |
| `updated_at` | `ru` | Auto-updated to current UTC time on every create/update |

##### Optional Validation Flags

| Flag | Effect |
|------|--------|
| `create_optional: True` | Field can be omitted in Create form |
| `update_optional: True` | Field can be omitted in Update form |

##### Model Permissions (`__onesite__.permissions`)
Controls which users can access the model and what operations they can perform.

**Role Hierarchy**: `developer >= admin >= user`

**Priority**: Default (`rcud`) > Model (`__onesite__.permissions`) > Field (`permissions`)

**Permissions Format** (new - supports per-role permissions):

```python
class Product(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "ru",      # user: read + update only
            "admin": "rcu",    # admin: full access
            "developer": "rcu", # developer: full access
        },
        "visible": {
            "user": True,      # user sees it in menu
            "admin": True,
            "developer": True,
        }
    }
```

**String Format** (backward compatible - same permission for all roles):

```python
__onesite__ = {"permissions": "rcud"}  # All roles get rcud (default)
__onesite__ = {"permissions": "rcu"}   # All roles get rcu
__onesite__ = {"permissions": "admin-rcu"}  # Only admin+ get access
__onesite__ = {"permissions": "developer-rcu"}  # Only developer gets access
```

**Default**: If `permissions` is not set, all roles get `rcud`.

**Permission Values** (field-level):

| Value | Access | Description |
|-------|--------|-------------|
| `r` | Read only | Field appears in CSV export, not in Create/Update forms |
| `rc` | Read + Create | Field in Create form, not in Update form |
| `ru` | Read + Update | Field in Update form, not in Create form |
| `rcu` | Full access | Field in all forms |

**Visible Config** (`__onesite__.visible`):

Controls menu visibility. Can be:
- **String**: `"admin"` (admin+ visible), `"developer"` (developer only)
- **Dict**: `{"user": True, "admin": True, "developer": False}`

**Default**: If `visible` is not set, menu visibility is determined by whether the role has any permission.

##### User Roles

The `User` model has a `role` field with three levels:

```python
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    DEVELOPER = "developer"
```

- **developer**: Full system access, can manage all models including system configs
- **admin**: Can manage models where role_permissions includes "admin"
- **user**: Can only access models where role_permissions includes "user"

> **Note**: The `is_superuser` field is deprecated. Use `role` instead for permission control.

##### Frontend Permission Effects

Based on role_permissions, the frontend conditionally renders:

| Permission | Frontend Effect |
|------------|-----------------|
| No `r` | Model hidden from left navigation menu |
| No `c` | Create button hidden |
| No `u` | Edit button and Action buttons hidden |
| No `d` | Delete button hidden |

##### Field-Level Configuration

**Field-level permissions** (controls Create/Update/Export):

```python
# String format (same permission for all roles)
sa_column_kwargs={"info": {"site_props": {
    "permissions": "rc",
    "create_optional": True,
    "update_optional": True,
}}}

# Dict format (per-role permissions) - inherits from model if not specified
sa_column_kwargs={"info": {"site_props": {
    "permissions": {
        "user": "r",           # user can only read
        "admin": "rcu",        # admin can create and update
        "developer": "rcu",     # developer has full access
    },
    "create_optional": True,
    "update_optional": True,
}}}
```

**Field Permission Priority**: Default (inherit from model) > Model config > Field config

When `permissions` is not specified on a field, it inherits from the model's `role_permissions` (with `d` removed since delete is model-level).

##### Special Model: User

- **`r` permission**: Field appears in CSV export headers
- **`c` permission**: Field is included in CSV import processing and Create form
- **`u` permission**: Field is included in Update form

**Example**: `permissions: "r"` makes a field read-only (exportable but not importable/editable).

##### Configuration Examples

**Per-role permissions** (new):
```python
class Product(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "ru",      # user can only read and update
            "admin": "rcu",    # admin has full access
            "developer": "rcu", # developer has full access
        }
    }
```

**Admin-only model** (only admin and developer can access):
```python
class AuditLog(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "admin": "rcu",
            "developer": "rcu",
        }
    }
```

**Developer-only model** (only developers can access):
```python
class SystemConfig(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "developer": "rcu",
        }
    }
```

**Public model** (all logged-in users can access):
```python
class Product(SQLModel, table=True):
    __onesite__ = {
        "permissions": "rcu"  # Or {"user": "rcu", "admin": "rcu", "developer": "rcu"}
    }
```

**Hidden menu but accessible API** (Notification pattern):
```python
class Notification(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "rcu",    # All users can call the API
            "admin": "rcu",
            "developer": "rcu",
        },
        "visible": {
            "user": False,    # But only admin+ see it in menu
            "admin": True,
            "developer": True,
        }
    }
```

**String format equivalent** (backward compatible):
```python
__onesite__ = {"permissions": "rcu"}  # All roles get rcu
__onesite__ = {"permissions": "admin-rcu"}  # admin+ only
__onesite__ = {"permissions": "developer-rcu"}  # developer only
```

##### Permission Summary

| Level | Default | Config Location | Notes |
|-------|---------|----------------|-------|
| Model | `rcud` | `__onesite__.permissions` | Controls API access and delete button |
| Field | Inherit model | `sa_column_kwargs.info.site_props` | `d` is stripped (delete is model-level) |
| `id` | `r` | Auto | Always read-only |
| `created_at` | `r` | Auto | Auto-set on create |
| `updated_at` | `ru` | Auto | Auto-updated on every write |

**Key Points:**
- Delete (`d`) is **model-level only**, not field-level
- Field permissions inherit from model config by default
- Special fields (`id`, `created_at`, `updated_at`) have fixed simplified permissions
- `user` role: lowest access, often restricted to read-only
- `admin` role: medium access, can manage most content
- `developer` role: highest access, can manage system configs

**Special Models:**
- **User**: `user` role can only access `/me` endpoint, admin cannot create developer role
- **Notification**: API accessible by all, menu visible only to admin+

**Special Case: User Model**

The User model has built-in special handling:

```python
class User(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "r",  # User can access /me endpoint with read
            "admin": "rcud",  # Admin can CRUD, but cannot create developer role
            "developer": "rcud",  # Developer has full access
        },
        "special_me_permissions": "ru",  # Special: user can access /me with ru
    }
```

This configuration means:
- **user role**: Can only access `/users/me` endpoint (read/update own profile). Redirected from user list page.
- **admin role**: Can CRUD users, but cannot create or promote to `developer` role.
- **developer role**: Has full access to all user operations including creating developer accounts.

Backend enforcement:
- Admin attempting to create/promote to `developer` role returns 403 error
- Regular users are redirected from `/users` to `/users/me` in the frontend

##### Special Model: Notification

The Notification model has built-in special handling:

```python
class Notification(SQLModel, table=True):
    __onesite__ = {
        "is_notification_table": True,
        "permissions": {
            "user": "rcu",    # All users can access via API
            "admin": "rcu",
            "developer": "rcu",
        },
        "visible": {
            "user": False,     # Not visible in menu
            "admin": True,     # Admin can see notifications menu
            "developer": True,
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

**Note**: The Notification model does **not** have an `updated_at` field - it uses `is_read` for tracking read status only.

This configuration means:
- **API Access**: All authenticated users can access notifications via API
- **Menu Visibility**: Only admin+ can see the Notifications menu item
- **Broadcast Support**: `user_id=None` with `broadcast=true` sends to all active users
- **Real-time Push**: Notifications are automatically pushed via WebSocket when created or read status changes

Required fields (names are fixed): `title`, `summary`, `content`, `created_at`, `is_read`, `user_id`.

#### Search & Filters
You can mark certain fields as searchable to generate a filter panel at the top of list pages.

```python
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    is_active: bool = Field(default=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    created_at: datetime = Field(sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
```

- `bool`: exact match (All/Yes/No)
- `Enum`: exact match (All + enum values)
- `str`: fuzzy contains (`ilike "%value%"`)
- `datetime`: range filter (from/to)

#### Foreign Key Labels
When a model has foreign keys, OneSite automatically resolves and displays the related record's human-readable label in list pages:

```python
class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )

class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    
    # This FK will display the author's name (not the ID) in list pages
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
```

**Label Field Selection**:
- OneSite uses the **first field** that is both `unique=True` and `is_search_field=True` as the label field
- Common pattern: Use `name`, `username`, `email`, or similar identifier fields
- If no `unique + is_search_field` field exists, falls back to the first `is_search_field` field
- **Recommendation**: FK target models should have at least one field with both `unique=True` and `is_search_field=True` for optimal SearchableSelect and list page display

**Generated Behavior**:
- **Backend**: Returns enriched data with `{fk_name}_label` fields (e.g., `author_id_label: "John Doe"`)
- **Frontend**: Displays the label in list pages, falls back to "ID: 123" if label is unavailable
- **Performance**: Uses batch fetching to avoid N+1 queries (single query per FK with `WHERE id IN (...)`)

#### JSON Fields (Object & Array)
OneSite supports two JSON field kinds:
- **Object JSON**: `Dict[str, Any]` (or `dict`)
- **Array JSON**: `List[Any]` (or `list`)

#### JSON Fields (BaseModel)
If you define a Pydantic model in advance, you can use it directly as a JSON field type.
OneSite will render a structured UI form for it, and you can switch between **UI mode** and **JSON mode**.

```python
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

class Gender(str, Enum):
    male = "male"
    female = "female"

class Test(BaseModel):
    name: str
    gender: Gender
    is_teacher: bool

class NestedJsonDemo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    t: Test = Field(sa_column=Column(JSON))
    ts: List[Test] = Field(default_factory=list, sa_column=Column(JSON))
```

- `t: Test`: Renders fields like `name`, `gender`, `is_teacher` as normal inputs/selects/switch.
- `ts: List[Test]`: Supports adding/removing multiple items, each item has the same UI form.
- You can always switch to JSON mode to paste/edit raw JSON directly.

**Recommended model definition (works across DBs that support JSON):**
```python
from typing import Any, Dict, List, Optional
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

class JsonDemo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    meta: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        schema_extra={"site_props": {"component": "json", "json_kind": "object"}},
    )

    tags: List[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        schema_extra={"site_props": {"component": "json", "json_kind": "array"}},
    )
```

- If you omit `component/json_kind`, OneSite will still infer JSON UI from `Dict[...]`/`List[...]` types.
- The generated UI provides a JSON editor (formatting on blur + basic validation).

#### Auto Refresh
Enable automatic data refreshing for list and detail views. This is useful for monitoring dashboards or real-time data.

```python
class DashboardMetric(SQLModel, table=True):
    # Enable auto-refresh every 5 seconds (5000ms)
    __table_args__ = {"info": {"site_props": {
        "auto_refresh": True, 
        "refresh_interval": 5000
    }}}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    value: float
```

- `auto_refresh`: `bool`. If `True`, adds an "Auto Refresh" toggle to the UI.
- `refresh_interval`: `int` (milliseconds). The default refresh interval (default: 5000ms). Users can change this in the UI.

#### Site Configuration (site_config.json)
You can customize the look and feel of your application by editing `site_config.json` in the project root.

```json
{
    "project_name": "My Awesome Project",
    "style": "anime",
    "radius": 1.0,
    "database_url": "sqlite:///./app.db"
}
```

- **style**: Presets for complete UI style. Each style includes full light/dark color system, border/input tone, font family, heading weight, card shadow, and page background texture.
    - `normal`: Professional SaaS style, clean white/blue system, balanced spacing and neutral shadow.
    - `industrial`: Mechanical dashboard style, colder grayscale palette, sharp corners, stronger borders and grid texture.
    - `anime`: High-saturation fantasy style, vibrant violet/cyan/yellow accents, large round corners and colorful glow shadows.
    - `cute`: Soft pastel style, warm pink/cream palette, extra round corners, gentle shadows and playful gradient texture.
    - Legacy aliases are still accepted for backward compatibility: `slate`, `blue`, `red`, `green`, `orange`, `purple`, `yellow`.
- **radius**: Optional global border radius override. If omitted, each style uses its own default radius.

### 4. Sync and Generate Code

Run the sync command to generate backend and frontend code based on your models. Use `--install` flag for the first run to install dependencies.

```bash
site sync --install
```

### 5. Run the Application (Local Development)

Start both backend and frontend servers with one command:

```bash
site run
```

- **Backend**: http://localhost:8000 (Docs: http://localhost:8000/docs)
- **Frontend**: http://localhost:5173

**Default Admin Credentials**:
- Email: `admin@example.com`
- Password: `admin`

### 6. Containerization & Deployment

OneSite makes it easy to build and run your application using Docker/Podman.

#### Build Images & Generate Configuration
This command builds the container images and generates a `docker-compose.yml` configured to use them.

```bash
# Build with default settings (Docker, tag: latest, port: 3000)
site build

# Or customize settings
site build --engine podman --tag v1.0 --port 8080
```

#### Run with Compose
Start the services using the generated configuration.

```bash
site compose up -d
```

- **Frontend**: http://localhost:3000 (or your custom port)
- **Backend**: http://localhost:8000 (internal to compose network)

## Project Structure

```
myproject/
├── site_config.json    # Project configuration
├── models/             # Define your SQLModel classes here
├── backend/
│   ├── app/
│   │   ├── api/        # Generated API endpoints
│   │   ├── cruds/     # Generated CRUD logic
│   │   ├── models/     # Synced models
│   │   ├── schemas/    # Generated Pydantic schemas
│   │   ├── services/   # Business logic
│   │   ├── core/       # Config, Security, DB
│   │   │   └── security.py # Password hashing & Auth
│   │   └── initial_data.py # Data seeding (Admin user)
│   ├── tests/          # Generated pytest tests
│   ├── uploads/        # User uploaded files
│   └── ...
└── frontend/
    ├── src/
        ├── components/ # UI Components (Button, Input, Modal, ImageUpload, etc.)
        ├── pages/      # Generated List/Edit Pages + Dashboard
        ├── services/   # Generated API Clients
        ├── stores/     # Generated State Management
        └── ...
```

## Commands Reference

- **`site init`**: Initialize an existing project. Creates `site_config.json` and/or `models/` with base models (User, SystemConfig, CustomConfig) if they don't exist.
- **`site create <name>`**: Create a new project scaffold.
- **`site sync [--install/-i]`**: Sync models and generate code. Use `-i` to install Python and Node dependencies.
- **`site run [component]`**: Run the project locally. `component` can be `backend`, `frontend`, or `all` (default).
- **`site build [--component/-c] [--engine/-e] [--tag/-t] [--port/-p]`**: Build container images and generate `docker-compose.yml`.
  - `--component`: `backend`, `frontend`, or `all` (default).
  - `--engine`: `docker` (default) or `podman`.
  - `--tag`: Image tag (default: `latest`).
  - `--port`: Frontend exposed port (default: `3000`).
- **`site compose <command> [args]...`**: Run docker-compose commands using the generated file.
  - Examples: `site compose up -d`, `site compose down`, `site compose logs -f`.

## Requirements

- Python 3.10+
- Node.js & npm (for frontend)
- Docker or Podman (optional, for containerization)

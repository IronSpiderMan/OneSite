# OneSite

OneSite is a powerful model-driven CLI tool that automatically generates a full-stack web application (FastAPI + React/Vite) from simple Python SQLModel definitions.

It automates the repetitive work of building CRUD APIs, database schemas, and frontend management pages, allowing you to focus on business logic.

## Features

- **Full-Stack Generation**: Generates Backend (FastAPI, SQLModel, Pydantic) and Frontend (React, Tailwind, Zustand, Lucide Icons).
- **Model-Driven**: Define your data models in standard Python code, and let OneSite handle the rest.
- **Auto CRUD & Validation**: Automatically generates Create, Read, Update, Delete APIs and UI, including unique constraints validation.
- **Search & Filters**: Mark fields as searchable to generate list-page filters (bool/enum/string contains/datetime range).
- **Smart UI Components**:
  - `bool` -> **Switch** / **Badge**
  - `Enum` -> **Select** / **Badge**
  - `datetime` -> **Text**
  - **Image Upload**: Detects image fields (e.g. `avatar`, `_image`) and generates file upload and preview components.
  - **File Attachment**: Detects file fields (e.g. `report_file`, `_file` suffix) and generates file upload components with built-in preview.
    - **Preview Support**: PDF, Word (docx), Excel (xlsx, csv), Markdown, Code/Text, Video, Audio, Images.
  - **Foreign Key**: Auto-detects foreign keys and generates searchable select dropdowns (`SearchableSelect`).
  - **Many-to-Many**: Supports M2M relationships via link tables, generating multi-select components.
  - **One-to-Many (Reverse FK)**: Displays related items in a paginated list on the detail page (e.g. Products under a Category). Configurable.
- **Better UX Defaults**: Delete confirmation dialogs; toast notifications for create/update.
- **Pagination**: Built-in standard pagination support for all list views.
- **Auto Refresh**: Configurable auto-refresh for real-time data monitoring.
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

### 1. Create a New Project

```bash
site create myproject
cd myproject
```

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
- If a link table contains extra non-FK fields (association table), OneSite will generate standalone CRUD pages/endpoints for it so you can edit those extra fields.
- Selection UI for both Foreign Keys and M2M uses `SearchableSelect`, which queries the target model list endpoint with `q=...` (fuzzy match on the target model's `search_field`).
- OneSite generates relationship endpoints like:
  - `GET /posts/{id}/tags` (targets related to a source item)
  - `GET /tags/{id}/posts` (reverse M2M: sources related to a target item)

##### Direction (Owner Side)
By default, OneSite injects the M2M `*_ids` field only on the "source" side of the link table.
Currently, the source/target side is inferred by foreign key field order in the link table:
- the first FK is treated as the source (gets `target_ids` in Create/Update)
- the second FK is treated as the target (gets reverse M2M endpoints and detail-page related list)

Example: `post_id` then `tag_id` means `Post` gets `tag_ids` and `GET /posts/{id}/tags`, while `Tag` gets `GET /tags/{id}/posts`.

#### Configuration Models (Settings Page)
OneSite reserves two special models for the unified `/settings` page:
- `SystemConfig` in `models/system_config.py`: server-persisted system settings, admin-only
- `CustomConfig` in `models/custom_config.py`: browser-persisted user preferences (localStorage), available to all users

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
    __onesite__ = {"config_role": "system", "permissions": "admin", "is_singleton": True}
    
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
Control field visibility and validation requirements for Create/Update operations.

```python
class User(SQLModel, table=True):
    # ...
    email: str = Field(unique=True) # Unique constraint validation
    password: str = Field(sa_column_kwargs={"info": {"site_props": {
        "permissions": "cu",          # 'c'=Create, 'u'=Update. 'r'=Read (omitted here, so password is never sent to frontend)
        "create_optional": False,     # Required when creating a user
        "update_optional": True       # Optional when updating (leave blank to keep current password)
    }}})
```

- `unique=True`: Adds a unique constraint to the field. OneSite automatically generates validation logic in Create/Update APIs to prevent duplicate entries (returns `400 Bad Request`).
- `permissions`: String with `r` (read), `c` (create), `u` (update). Default is `rcu`.
- `create_optional`: If `True`, field is not required in Create form.
- `update_optional`: If `True`, field is not required in Update form.

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
├── models/             # Define your SQLModel classes here
├── backend/
│   ├── app/
│   │   ├── api/        # Generated API endpoints
│   │   ├── cruds/      # Generated CRUD logic
│   │   ├── models/     # Synced models
│   │   ├── schemas/    # Generated Pydantic schemas
│   │   ├── services/   # Business logic
│   │   ├── core/       # Config, Security, DB
│   │   │   └── security.py # Password hashing & Auth
│   │   └── initial_data.py # Data seeding (Admin user)
│   ├── uploads/        # User uploaded files
│   └── ...
└── frontend/
    ├── src/
        ├── components/ # UI Components (Button, Input, Modal, ImageUpload, etc.)
        ├── pages/      # Generated List/Edit Pages
        ├── services/   # Generated API Clients
        ├── stores/     # Generated State Management
        └── ...
```

## Commands Reference

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

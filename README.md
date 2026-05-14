# OneSite

OneSite is a model-driven CLI tool that generates full-stack web applications (FastAPI + React/Vite) from SQLModel definitions.

```bash
pip install onesite
```

## Quick Start

```bash
# Create a new project
site create myproject
cd myproject

# Define your SQLModel classes in models/
# Then sync to generate backend and frontend code
site sync --install

# Run both servers
site run
```

- Backend: http://localhost:8000 (Docs: http://localhost:8000/docs)
- Frontend: http://localhost:5173
- Default admin: `admin@example.com` / `admin`

## Defining Models

### Basic Model

```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    is_active: bool = True
```

### Foreign Key

```python
class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

FK fields auto-detect their target table. List pages display the related record's label (first `unique + is_search_field` field) instead of raw IDs.

### Many-to-Many

```python
class PostTagLink(SQLModel, table=True):
    __onesite__ = {"is_link_table": True}
    post_id: Optional[int] = Field(default=None, foreign_key="post.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
```

M2M link tables generate multi-select components on the source model's form. If a link table has extra non-FK fields, it generates standalone CRUD pages for editing them.

### User-Owned Resources (`owner_field`)

Mark a model as user-owned so non-admin users can only see/edit their own records:

```python
class Item(SQLModel, table=True):
    __onesite__ = {
        "owner_field": "owner_id",
    }
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

- **Users** only see their own items (list filtered by `owner_id = current_user.id`)
- **Admins/developers** see all items
- Create forces `owner_id = current_user.id` for non-admin users
- Detail/update/delete return 404 if the item doesn't belong to the current user
- Frontend shows "My Items" in the menu and page title for user role

## Permission System

Three-layer permission system: model-level CRUD, field-level CRU, and frontend visibility.

```python
class Product(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "ru",       # read + update
            "admin": "rcud",    # full access
            "developer": "rcud",
        },
        "visible": ["admin", "developer"],  # menu visibility
    }
```

Permission chars: `c` = create, `r` = read, `u` = update, `d` = delete.

Role hierarchy: `developer >= admin >= user`.

**Field-level permissions** control field visibility in forms:

```python
email: str = Field(sa_column_kwargs={"info": {"site_props": {
    "permissions": {
        "user": "r",
        "admin": "rcu",
        "developer": "rcu",
    }
}}})
```

Special field defaults: `id` = read-only, `created_at` = read-only, `updated_at` = read+update.

## Key Features

- **Code generation**: Backend (FastAPI, SQLModel, Pydantic) + Frontend (React, Tailwind, Zustand)
- **CRUD with validation**: Auto-generated endpoints and forms with unique constraint checks
- **Search & filters**: Mark fields with `is_search_field` to generate filter panels
- **Smart FK display**: Shows related record labels instead of raw IDs
- **File & image upload**: Auto-detected by field name conventions (`_image`, `_file`, `avatar`, etc.)
- **JSON fields**: Support for `Dict`, `List`, and Pydantic models as JSON columns with structured editors
- **CSV import/export**: Configure `importable`/`exportable` on any model
- **Notifications**: Optional notification center with WebSocket real-time push
- **Dashboard**: Auto-generated stats cards and charts (bar, line, pie)
- **Scheduled tasks**: Cron and interval tasks via APScheduler, manageable from the UI
- **Internationalization**: EN/ZH locale files generated from model translations
- **Themes**: Built-in styles (normal, industrial, anime, cute)
- **Containerization**: Docker/Podman build and Compose support
- **Authentication**: JWT-based login, role-based access control
- **Singleton models**: Config-style models (e.g., `SystemConfig`) with singleton endpoints
- **Custom actions**: One-click buttons with conditional logic and field updates
- **Auto refresh**: Real-time data monitoring with configurable intervals

## Site Configuration

Customize via `site_config.json` in the project root:

```json
{
    "project_name": "My Project",
    "style": "anime",
    "radius": 1.0,
    "database_url": "sqlite:///./app.db",
    "nav_order": ["user", "product", "tag"]
}
```

Styles: `normal`, `industrial`, `anime`, `cute` — full color systems, typography, and shadows.

## Project Structure

```
myproject/
├── site_config.json    # Project configuration
├── models/             # SQLModel definitions (source of truth)
├── backend/
│   ├── app/
│   │   ├── api/endpoints/  # Generated REST endpoints
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── cruds/          # CRUD operations
│   │   ├── models/         # Synced SQLModel classes
│   │   ├── core/           # Config, security, database
│   │   └── initial_data.py # Admin user seeding
│   └── tests/
└── frontend/
    └── src/
        ├── pages/      # Generated list/detail pages
        ├── services/   # API clients
        ├── stores/     # Zustand state
        └── components/ # UI components
```

## Commands

| Command | Description |
|---------|-------------|
| `site init` | Initialize config and base models in existing project |
| `site create <name>` | Create new project scaffold |
| `site sync [--install]` | Sync models and generate code |
| `site run [backend\|frontend\|all]` | Start development servers |
| `site build [--engine] [--tag] [--port]` | Build Docker/Podman images |
| `site compose up\|down\|logs -f` | Run docker-compose commands |

## Requirements

- Python 3.10+
- Node.js & npm (for frontend)
- Docker or Podman (optional, for containerization)

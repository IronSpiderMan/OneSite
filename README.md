# OneSite

OneSite is a powerful model-driven CLI tool that automatically generates a full-stack web application (FastAPI + React/Vite) from simple Python SQLModel definitions.

It automates the repetitive work of building CRUD APIs, database schemas, and frontend management pages, allowing you to focus on business logic.

## Features

- **Full-Stack Generation**: Generates Backend (FastAPI, SQLModel, Pydantic) and Frontend (React, Tailwind, Zustand, Lucide Icons).
- **Model-Driven**: Define your data models in standard Python code, and let OneSite handle the rest.
- **Auto CRUD**: Automatically generates Create, Read, Update, Delete APIs and UI.
- **Smart UI Components**:
  - `bool` -> **Switch** / **Badge**
  - `Enum` -> **Select** / **Badge**
  - `datetime` -> **Text**
  - **Image Upload**: Detects image fields (e.g. `avatar`, `_image`) and generates file upload and preview components.
  - **File Attachment**: Detects file fields (e.g. `report_file`, `_file` suffix) and generates file upload components with built-in preview.
    - **Preview Support**: PDF, Word (docx), Excel (xlsx, csv), Markdown, Code/Text, Video, Audio, Images.
  - **Foreign Key**: Auto-detects foreign keys and generates searchable select dropdowns (`SearchableSelect`).
  - **Many-to-Many**: Supports M2M relationships via link tables, generating multi-select components.
- **Pagination**: Built-in standard pagination support for all list views.
- **Authentication & Security**:
  - **Built-in Login**: Modern login page with JWT authentication.
  - **Protected Routes**: Automatic auth guards for frontend pages.
  - **Secure APIs**: CRUD endpoints default to authenticated access; static files are public.
  - **User Management**: Secure password hashing and role-based field access.
- **Containerization**: Built-in support for Docker/Podman build and Compose.

## Installation

```bash
# Clone the repository
git clone https://github.com/IronSpiderMan/OneSite.git
cd OneSite

# Install the tool in editable mode
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
    # Foreign Key to User (naming convention: target_model_lower + _id)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

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
    __table_args__ = {"info": {"site_props": {"is_link_table": True}}}
    
    post_id: Optional[int] = Field(default=None, foreign_key="post.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
```
OneSite will automatically inject a `tag_ids` field into the `Post` form, allowing you to select multiple Tags.

### 3. Advanced Configuration

You can customize field behavior using `site_props` in `sa_column_kwargs`.

#### Field Permissions & Validation
Control field visibility and validation requirements for Create/Update operations.

```python
class User(SQLModel, table=True):
    # ...
    password: str = Field(sa_column_kwargs={"info": {"site_props": {
        "permissions": "cu",          # 'c'=Create, 'u'=Update. 'r'=Read (omitted here, so password is never sent to frontend)
        "create_optional": False,     # Required when creating a user
        "update_optional": True       # Optional when updating (leave blank to keep current password)
    }}})
```

- `permissions`: String with `r` (read), `c` (create), `u` (update). Default is `rcu`.
- `create_optional`: If `True`, field is not required in Create form.
- `update_optional`: If `True`, field is not required in Update form.

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

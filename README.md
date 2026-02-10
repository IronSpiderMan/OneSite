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
  - **Foreign Key**: Auto-detects foreign keys and generates searchable select dropdowns (`SearchableSelect`).
  - **Many-to-Many**: Supports M2M relationships via link tables, generating multi-select components.
- **Pagination**: Built-in standard pagination support for all list views.
- **Authentication**: Built-in JWT authentication and User management.

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

### 3. Sync and Generate Code

Run the sync command to generate backend and frontend code based on your models. Use `--install` flag for the first run to install dependencies.

```bash
site sync --install
```

### 4. Run the Application

Start both backend and frontend servers with one command:

```bash
site run
```

- **Backend**: http://localhost:8000 (Docs: http://localhost:8000/docs)
- **Frontend**: http://localhost:5173

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
│   │   └── services/   # Business logic
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
- **`site run [component]`**: Run the project. `component` can be `backend`, `frontend`, or `all` (default).

## Requirements

- Python 3.10+
- Node.js & npm (for frontend)

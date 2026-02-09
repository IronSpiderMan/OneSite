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
  - `datetime` -> **Date Picker** (Coming soon) / Text
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

Add your models to the `models/` directory. For example, create `models/product.py`:

```python
from typing import Optional
from sqlmodel import Field, SQLModel
from enum import Enum

class Category(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True
    category: Category = Category.ELECTRONICS
```

### 3. Sync and Generate Code

Run the sync command to generate backend and frontend code based on your models. Use `--install` flag for the first run to install dependencies.

```bash
site sync --install
```

This command will:
1. Copy models to the backend.
2. Generate Database Schemas (Pydantic).
3. Generate CRUD operations and API Endpoints.
4. Generate Frontend Services (Axios), Stores (Zustand), and Pages (React components).
5. Update Routing and Menus.

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
│   │   ├── core/       # Config, Security, DB
│   │   ├── cruds/      # Generated CRUD logic
│   │   ├── models/     # Synced models
│   │   ├── schemas/    # Generated Pydantic schemas
│   │   └── services/   # Business logic
│   └── ...
└── frontend/
    ├── src/
    │   ├── components/ # UI Components (Button, Input, Modal, etc.)
    │   ├── pages/      # Generated List/Edit Pages
    │   ├── services/   # Generated API Clients
    │   ├── stores/     # Generated State Management
    │   └── ...
    └── ...
```

## Commands Reference

- **`site create <name>`**: Create a new project scaffold.
- **`site sync [--install/-i]`**: Sync models and generate code. Use `-i` to install Python and Node dependencies.
- **`site run [component]`**: Run the project. `component` can be `backend`, `frontend`, or `all` (default).

## Requirements

- Python 3.10+
- Node.js & npm (for frontend)

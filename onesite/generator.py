import os
import sys
import importlib
import inspect
import pkgutil
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
from sqlmodel import SQLModel
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from pydantic_core import PydanticUndefined

console = Console()

TEMPLATE_DIR = Path(__file__).parent / "templates" / "codegen"

def get_model_fields(model_cls):
    fields = []
    # Inspect SQLModel fields
    for name, field in model_cls.model_fields.items():
        # Get permissions from sa_column_kwargs -> info -> site_props -> permissions
        # OR fallback to json_schema_extra if available (for future proofing)
        
        sa_column_kwargs = getattr(field, "sa_column_kwargs", {})
        if sa_column_kwargs is PydanticUndefined or sa_column_kwargs is None:
            sa_column_kwargs = {}
            
        info = sa_column_kwargs.get("info", {})
        site_props = info.get("site_props", {})
        
        if not site_props:
            # Fallback to json_schema_extra
            if hasattr(field, "json_schema_extra"):
                 json_schema_extra = field.json_schema_extra
                 if json_schema_extra is PydanticUndefined or json_schema_extra is None:
                     json_schema_extra = {}
                 site_props = json_schema_extra.get("site_props", {})
        
        permissions = site_props.get("permissions", "rcu") # Default: Read, Create, Update
        create_optional = site_props.get("create_optional", False)
        update_optional = site_props.get("update_optional", False)
        allow_download = site_props.get("allow_download", True)
        
        # Force 'id' to be read-only if permissions not explicitly set to something else that includes write (unlikely)
        # Or better, just force 'r' for 'id' unless user really knows what they are doing.
        if name == 'id':
            permissions = 'r'

        console.print(f"Debug: Field {name} - Perms: {permissions}")
        
        # Determine python type string (simplified)
        type_annotation = field.annotation
        type_str = str(type_annotation)
        
        # Debugging type annotation
        console.print(f"Debug: Field {name} - Type Annotation: {type_annotation} (Type: {type(type_annotation)}) - Type Str: {type_str}")

        is_enum = False
        enum_values = []
        
        # Check for Enum
        if inspect.isclass(type_annotation) and issubclass(type_annotation, (str, int)) and hasattr(type_annotation, "__members__"):
             is_enum = True
             enum_values = [e.value for e in type_annotation]
             type_str = "str" # Treat enum as string for now in frontend

        # Improved Type Detection
        if "int" in type_str: type_str = "int"
        elif "str" in type_str: type_str = "str"
        # Check for 'bool' in string OR if annotation is explicitly bool class
        elif "bool" in type_str or type_annotation is bool: type_str = "bool"
        elif "float" in type_str: type_str = "float"
        elif "datetime" in type_str: type_str = "datetime"
        else: type_str = "str" # Fallback
        
        # Save UI type before wrapping with Optional
        ui_type = type_str
        
        # Check for image component
        if site_props.get("component") == "image":
            ui_type = "image"
        # Check for file component
        elif site_props.get("component") == "file":
            ui_type = "file"
        # Heuristic for image fields if type is string
        elif ui_type == "str" and (
            name.endswith("_image") or 
            name.endswith("_img") or 
            name.endswith("_photo") or 
            name == "avatar" or
            name == "image" or
            name == "photo" or
            name == "logo"
        ):
             ui_type = "image"
        # Heuristic for file fields if type is string
        elif ui_type == "str" and (
            name.endswith("_file") or
            name.endswith("_attachment") or
            name == "file" or
            name == "attachment"
        ):
             ui_type = "file"
        
        # Check metadata for search field
        is_search_field = site_props.get("is_search_field", False)

        # Determine label for i18n
        # Default: models.{model_name}.fields.{field_name}
        # If user provides explicit label in site_props, use it (though better to use i18n key)
        # We will use 'label_key' to store the i18n key
        model_name_lower = model_cls.__name__.lower()
        default_label_key = f"models.{model_name_lower}.fields.{name}"
        label_key = site_props.get("label", default_label_key)
        
        # Extract translations if available
        translations = site_props.get("translations", {})
        
        # Check foreign key info from site_props or infer from name
        # We assume FK fields are named like `modelname_id` or explicit `foreign_key` in sa_column_args
        # But SQLModel puts foreign_key in Field(foreign_key=...) which maps to sa_column_args?
        # Actually SQLModel Field(foreign_key=...) puts it in sa_column_kwargs['foreign_key'] if using sa_column_kwargs explicitly
        # But standard SQLModel Field(foreign_key="...") handles it differently in pydantic model fields.
        # We need to inspect the field definition more closely or rely on naming convention + metadata for now.
        
        # Let's check naming convention for MVP: if ends with _id, it might be a FK
        fk_info = None
        if name.endswith("_id") and name != "id":
             target_model_name = name[:-3] # e.g. category_id -> category
             # Capitalize first letter to guess model class name
             target_model_class = target_model_name.capitalize()
             fk_info = {
                 "name": name,  # Add field name here
                 "target_model": target_model_class,
                 "target_service": target_model_name,
                 "target_endpoint": f"{target_model_name}s",
                 "label_field": "name" # Default guess
             }
        
        # Check if optional
        is_optional = not field.is_required()
        if is_optional:
            type_str = f"Optional[{type_str}]"
            
        fields.append({
            "name": name,
            "type": type_str,
            "ui_type": ui_type,
            "permissions": permissions,
            "create_optional": create_optional,
            "update_optional": update_optional,
            "required": field.is_required(),
            "default": field.default,
            "is_enum": is_enum,
            "enum_values": enum_values,
            "is_search_field": is_search_field,
            "fk_info": fk_info,
            "allow_download": allow_download,
            "label_key": label_key,
            "translations": translations
        })
    
    # Post-process fields to determine search field if not explicitly set
    # Only one search field per model for now (for the fuzzy search)
    has_explicit_search = any(f.get("is_search_field") for f in fields)
    if not has_explicit_search:
        # Guess: name, title, label, slug, email, username
        guess_candidates = ["name", "title", "label", "slug", "email", "username", "full_name"]
        for candidate in guess_candidates:
            found = next((f for f in fields if f["name"] == candidate), None)
            if found:
                found["is_search_field"] = True
                break
    
    # If still no search field, maybe use the first string field?
    if not any(f.get("is_search_field") for f in fields):
         first_str = next((f for f in fields if f["ui_type"] == "str" and not f["is_enum"]), None)
         if first_str:
             first_str["is_search_field"] = True

    # Identify if this is a link table (Many-to-Many)
    # Rule: 
    # 1. Has explicit metadata `is_link_table`
    # 2. OR: Has 2+ foreign keys AND no other required business fields (ignoring id, created_at, etc)
    # For now, let's just stick to checking if it's a valid model to generate.
    # We will filter found_models later.
    
    # Also collect foreign keys for the model context
    foreign_keys = [f["fk_info"] for f in fields if f["fk_info"]]
    # Remove duplicates if any (though usually 1 field = 1 fk)
    
    # Determine the search field name for this model to pass to context
    search_field = next((f["name"] for f in fields if f.get("is_search_field")), "id")
    
    # Update fk_info with the correct label_field (which is the search_field of the target model)
    # We can't do this here easily because we don't have access to other models yet.
    # We will do a post-processing pass in generate_code() or let the frontend template assume 
    # the target model's search field is what we want (which is usually true).
    # But wait, we set 'label_field': 'name' as default guess in line 96.
    # We should update this if possible.
    # For now, let's just leave it as 'name' default, but maybe we can be smarter.
    # Actually, the best place is in generate_code after all models are parsed.

    # Check if is_link_table metadata exists
    is_link_table = False
    translations = {}
    if hasattr(model_cls, "__table_args__") and isinstance(model_cls.__table_args__, dict):
        info = model_cls.__table_args__.get("info", {})
        site_props = info.get("site_props", {})
        is_link_table = site_props.get("is_link_table", False)
        translations = site_props.get("translations", {})

    return fields, foreign_keys, search_field, is_link_table, translations

def generate_file(template_name: str, context: Dict, output_path: Path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    content = template.render(context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    console.print(f"Generated {output_path}")

def load_site_config(cwd: Path) -> Dict[str, Any]:
    config_path = cwd / "site_config.json"
    if config_path.exists():
        import json
        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            console.print(f"[red]Error loading site_config.json: {e}[/red]")
    return {}

def sync_env_files(config: Dict[str, Any], backend_path: Path, frontend_path: Path):
    # Backend .env
    backend_env = backend_path / ".env"
    # Update .env (create or sync)
    if True:
        # Let's read existing env if any, and update keys from config.
        env_content = ""
        if backend_env.exists():
            env_content = backend_env.read_text()
        
        # Simple key-value update (naive implementation)
        # Better: parse env, update keys, write back.
        new_keys = {
            "PROJECT_NAME": config.get("project_name"),
            "DATABASE_URI": config.get("database_url"),
            "SECRET_KEY": config.get("secret_key"),
            "FIRST_SUPERUSER": config.get("first_superuser", "admin@example.com"),
            "FIRST_SUPERUSER_PASSWORD": config.get("first_superuser_password", "admin"),
        }
        
        # Add CORS origins to .env
        import json
        allowed_origins = config.get("allowed_origins", [])
        if allowed_origins:
             new_keys["BACKEND_CORS_ORIGINS"] = json.dumps(allowed_origins)
        
        lines = env_content.splitlines()
        existing_keys = {}
        for line in lines:
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                existing_keys[key.strip()] = val.strip()
        
        updated_lines = []
        # Update existing lines
        for line in lines:
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key = key.strip()
                if key in new_keys:
                    updated_lines.append(f"{key}={new_keys[key]}")
                    del new_keys[key]
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Append new keys
        for key, val in new_keys.items():
             updated_lines.append(f"{key}={val}")
             
        backend_path.mkdir(parents=True, exist_ok=True)
        backend_env.write_text("\n".join(updated_lines))
        console.print(f"Synced backend .env")

    # Frontend .env
    frontend_env = frontend_path / ".env"
    # Frontend needs VITE_API_URL and maybe VITE_UPLOAD_DIR (if needed)
    # But usually VITE_API_URL is sufficient as /uploads is relative or proxied.
    # We'll just ensure VITE_API_URL is set correctly if we know the backend port?
    # Actually, config doesn't have port info usually. Defaults to localhost:8000.
    # If user changes it, they change .env manually?
    # Or we can add api_url to site_config.
    # Default to relative path to use proxy
    api_url = config.get("api_url", "/api/v1")
    
    # Check existing frontend .env
    f_env_content = ""
    if frontend_env.exists():
        f_env_content = frontend_env.read_text()
        
    if "VITE_API_URL" not in f_env_content:
        frontend_path.mkdir(parents=True, exist_ok=True)
        with frontend_env.open("a") as f:
            f.write(f"\nVITE_API_URL={api_url}\n")
        console.print(f"Updated frontend .env with VITE_API_URL")
    else:
        # Update existing VITE_API_URL
        lines = f_env_content.splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith("VITE_API_URL="):
                updated_lines.append(f"VITE_API_URL={api_url}")
            else:
                updated_lines.append(line)
        frontend_env.write_text("\n".join(updated_lines))
        console.print(f"Updated frontend .env VITE_API_URL to {api_url}")

def generate_code():
    # Assume we are in the project root
    cwd = Path(os.getcwd())
    site_config = load_site_config(cwd)
    
    # Defaults
    site_config.setdefault("project_name", "MyApp")
    site_config.setdefault("database_url", "sqlite:///./app.db")
    site_config.setdefault("upload_dir", "uploads")
    site_config.setdefault("secret_key", "changeme")
    site_config.setdefault("allowed_origins", [
        "http://localhost:5173", 
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ])
    
    backend_path = cwd / "backend"
    
    # Sync .env files
    sync_env_files(site_config, backend_path, cwd / "frontend")

    if not backend_path.exists():
        console.print("[red]Backend directory not found. Are you in the project root?[/red]")
        return

    # 0. Sync models from root/models to backend/app/models
    # AND ALSO sync core models from template/models to backend/app/models if they don't exist in root/models
    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    
    # Template models dir
    template_models_dir = Path(__file__).parent / "templates" / "models"
    
    if not models_dest_dir.exists():
        models_dest_dir.mkdir(parents=True, exist_ok=True)
        (models_dest_dir / "__init__.py").touch()

    # Priority 1: Sync from project's models/ folder (User's custom models)
    if models_src_dir.exists():
        console.print(f"[green]Syncing models from {models_src_dir} to {models_dest_dir}...[/green]")
        for model_file in models_src_dir.glob("*.py"):
            shutil.copy2(model_file, models_dest_dir / model_file.name)
            console.print(f"Synced model: {model_file.name}")
    
    # Priority 2: Sync base models (like User) from templates if they are not in project's models/
    # This allows us to update the User model definition in the tool and have it propagate
    # UNLESS the user has overridden it in their project models/
    if template_models_dir.exists():
         for model_file in template_models_dir.glob("*.py"):
             # If user has a model with same name in models/, don't overwrite it from template
             # But if user is relying on default User model, we want to update it.
             # Wait, usually `site sync` assumes project root `models/` is the source of truth.
             # If `models/user.py` exists in project, we use it.
             # If not, we might fall back to backend/app/models/user.py which might be stale.
             # The issue here is: The user edited `onesite/templates/models/user.py` (the tool's template),
             # but `site sync` only looks at `project/models/`.
             
             # If the user wants to update the User model, they should probably copy it to `project/models/` first?
             # OR, we should copy from template to `backend/app/models` if not present in `project/models/`.
             
             target_in_project = models_src_dir / model_file.name
             if not target_in_project.exists():
                 # Not in project custom models, so we can update the backend copy from template
                 shutil.copy2(model_file, models_dest_dir / model_file.name)
                 console.print(f"Synced base model from template: {model_file.name}")
             else:
                 console.print(f"Skipping template model {model_file.name} (overridden in project)")

    sys.path.append(str(backend_path))
    
    # Reload modules to pick up changes
    # For simplicity, we just import
    try:
        import app.models
    except ImportError as e:
        console.print(f"[red]Could not import app.models: {e}[/red]")
        return

    # Find all model files
    models_dir = backend_path / "app" / "models"
    # Recursively find all .py files in models directory to support subdirectories if needed, 
    # but for now simple glob is fine. 
    # Important: glob returns Path objects, we need relative path to models_dir for module name if nested
    # But current structure is flat.
    model_files = [f.stem for f in models_dir.glob("*.py") if f.stem != "__init__"]
    
    found_models = []

    # Ensure we check sys.modules for any existing loaded models and reload them
    # This is crucial because if we just import, python might use cached version
    
    # Also we need to make sure we are importing from the correct path.
    # We added backend_path to sys.path, so 'app.models' should be resolvable.
    
    for module_name in model_files:
        full_module_name = f"app.models.{module_name}"
        
        try:
            if full_module_name in sys.modules:
                module = importlib.reload(sys.modules[full_module_name])
            else:
                module = importlib.import_module(full_module_name)
        except ImportError as e:
            console.print(f"[red]Error importing {full_module_name}: {e}[/red]")
            continue
        
        # Inspect classes
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, SQLModel) and obj is not SQLModel:
                # Check if it is a table model (usually checking table=True in config, but SQLModel stores it differently)
                # We'll assume if it's in models/ and inherits SQLModel, we want to generate code for it.
                # A safer check:
                if hasattr(obj, "metadata") and getattr(obj, "__table__", None) is not None:
                     fields, foreign_keys, search_field, is_link_table, translations = get_model_fields(obj)
                     
                     # Special handling for User model to add virtual 'password' field if not present
                     # Moving this logic out of get_model_fields to keep it clean or handle here
                     if name == 'User':
                        has_password = any(f['name'] == 'password' for f in fields)
                        if not has_password:
                             fields.append({
                                 "name": "password",
                                 "type": "str",
                                 "ui_type": "str",
                                 "permissions": "cu", # Create and Update
                                 "create_optional": False,
                                 "update_optional": True,
                                 "required": True,
                                 "default": PydanticUndefined,
                                 "is_search_field": False,
                                 "fk_info": None
                             })
                             
                     found_models.append({
                         "name": name,
                         "module_name": module_name, # Save the filename/module name
                         "lower_name": name.lower(),
                         "fields": fields,
                         "foreign_keys": foreign_keys,
                         "search_field": search_field,
                         "is_link_table": is_link_table,
                         "translations": translations
                     })
    
    # Post-process models to update FK label fields and collect readable fields
    # Now that we have all models and their search_fields, we can update fk_info
    model_map = {m["name"]: m for m in found_models}
    for model in found_models:
        for fk in model["foreign_keys"]:
            target_model = model_map.get(fk["target_model"])
            if target_model:
                fk["label_field"] = target_model["search_field"]
                # Collect readable fields for the target model
                # Filter out sensitive fields like password
                fk["target_readable_fields"] = [
                    f for f in target_model["fields"] 
                    if 'r' in f["permissions"] and f["name"] != "password" and not f.get("fk_info")
                ]
                console.print(f"Debug: Updated FK {model['name']} -> {fk['target_model']} label to {fk['label_field']}")
    
    # Process Link Tables (M2M)
    # Strategy: Inject m2m fields into the source model (first FK)
    for model in found_models:
        if model["is_link_table"]:
            fks = model["foreign_keys"]
            if len(fks) >= 2:
                # Assume 1st FK is Source, 2nd FK is Target
                source_fk = fks[0]
                target_fk = fks[1]
                
                source_model_name = source_fk["target_model"]
                target_model_name = target_fk["target_model"]
                
                source_model = model_map.get(source_model_name)
                target_model = model_map.get(target_model_name)
                
                if source_model and target_model:
                    # Inject virtual field into Source Model
                    m2m_field_name = f"{target_model['lower_name']}_ids"
                    
                    console.print(f"Debug: Injecting M2M field '{m2m_field_name}' into {source_model_name} (via {model['name']})")
                    
                    source_model["m2m_fields"] = source_model.get("m2m_fields", [])
                    source_model["m2m_fields"].append({
                        "name": m2m_field_name,
                        "target_model": target_model_name,
                        "target_service": target_fk["target_service"],
                        "target_endpoint": target_fk["target_endpoint"],
                        "label_field": target_fk["label_field"], # Already updated in previous loop
                        "link_model": model["name"],
                        "link_module": model["module_name"], # Pass the filename of the link table
                        "source_fk_field": source_fk["name"], # Field in link table pointing to source
                        "target_fk_field": target_fk["name"]  # Field in link table pointing to target
                    })

    # Sync pagination schema
    pagination_schema_src = Path(__file__).parent / "templates" / "backend" / "app" / "schemas" / "pagination.py"
    pagination_schema_dst = backend_path / "app" / "schemas" / "pagination.py"
    if pagination_schema_src.exists():
        if not pagination_schema_dst.parent.exists():
            pagination_schema_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pagination_schema_src, pagination_schema_dst)
        console.print(f"Synced pagination schema to {pagination_schema_dst}")

    # Sync token schema
    token_schema_src = Path(__file__).parent / "templates" / "backend" / "app" / "schemas" / "token.py"
    token_schema_dst = backend_path / "app" / "schemas" / "token.py"
    if token_schema_src.exists():
        if not token_schema_dst.parent.exists():
            token_schema_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(token_schema_src, token_schema_dst)
        console.print(f"Synced token schema to {token_schema_dst}")

    # Generate code for each model
    for model in found_models:
        # Skip generating views/APIs for link tables
        if model["is_link_table"]:
            continue
            
        context = {"model": model}
        
        is_user_model = model['name'] == 'User'
        
        # 1. Schemas
        schema_tpl = "user_schema.py.j2" if is_user_model else "schema.py.j2"
        generate_file(schema_tpl, context, backend_path / "app" / "schemas" / f"{model['lower_name']}.py")
        
        # 2. CRUD
        crud_tpl = "user_crud.py.j2" if is_user_model else "crud.py.j2"
        generate_file(crud_tpl, context, backend_path / "app" / "cruds" / f"{model['lower_name']}.py")
        
        # 3. Service
        service_tpl = "user_service.py.j2" if is_user_model else "service.py.j2"
        generate_file(service_tpl, context, backend_path / "app" / "services" / f"{model['lower_name']}.py")
        
        # 4. API
        generate_file("api.py.j2", context, backend_path / "app" / "api" / "endpoints" / f"{model['lower_name']}.py")
        
        # 5. Frontend Service
        generate_file("frontend_service.ts.j2", context, cwd / "frontend" / "src" / "services" / f"{model['lower_name']}.ts")
        
        # 6. Frontend Store
        generate_file("frontend_store.ts.j2", context, cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts")

        # 7. Frontend View (Page List)
        generate_file("frontend_page_list.tsx.j2", context, cwd / "frontend" / "src" / "pages" / f"{model['lower_name']}" / "index.tsx")

        # 8. Frontend View (Page Detail)
        generate_file("frontend_page_detail.tsx.j2", context, cwd / "frontend" / "src" / "pages" / f"{model['lower_name']}" / "detail.tsx")

    # Sync UI Components (Ensure they exist in the target project)
    # We copy from the template directory to the target project
    template_components_dir = Path(__file__).parent / "templates" / "frontend" / "src" / "components" / "ui"
    target_components_dir = cwd / "frontend" / "src" / "components" / "ui"
    
    if template_components_dir.exists():
        if not target_components_dir.exists():
            target_components_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files if they don't exist or update them? 
        # For now, let's copy if missing to avoid overwriting user changes, or overwrite? 
        # Since this is a sync tool, overwriting might be expected for 'core' components, but risky.
        # Let's just ensure they exist.
        for item in template_components_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_components_dir / item.name)
        console.print(f"Synced UI components to {target_components_dir}")

    # Sync Utils
    template_utils_dir = Path(__file__).parent / "templates" / "frontend" / "src" / "utils"
    target_utils_dir = cwd / "frontend" / "src" / "utils"
    if template_utils_dir.exists():
        if not target_utils_dir.exists():
            target_utils_dir.mkdir(parents=True, exist_ok=True)
        for item in template_utils_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_utils_dir / item.name)
        console.print(f"Synced Utils to {target_utils_dir}")


    # Sync Config Files (package.json, tailwind.config.js, etc.)
    # This is important when templates are updated.
    config_files = [
        "package.json",
        "tailwind.config.js",
        "postcss.config.js",
        "tsconfig.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "index.html",
        "src/main.tsx",
        "src/App.tsx",
        "src/index.css",
        "src/components/ui/button.tsx",
        "src/components/ui/input.tsx",
        "src/components/ui/label.tsx",
        "src/components/ui/modal.tsx",
        "src/components/ui/table.tsx",
        "src/components/ui/badge.tsx",
        "src/components/ui/switch.tsx",
        "src/components/ui/select.tsx",
        "src/components/ui/card.tsx",
        "src/components/ui/separator.tsx",
        "src/components/ui/image-upload.tsx",
        "src/components/ui/file-upload.tsx",
        "src/components/ui/file-preview.tsx",
        "src/components/Layout.tsx",
        "src/utils/request.ts",
        "src/pages/Login.tsx",
        "src/pages/Settings.tsx",
        "src/vite-env.d.ts",
        "src/i18n.ts"
    ]
    template_frontend_root = Path(__file__).parent / "templates" / "frontend"
    target_frontend_root = cwd / "frontend"
    
    # Sync src/lib (e.g. utils.ts)
    template_lib_dir = template_frontend_root / "src" / "lib"
    target_lib_dir = target_frontend_root / "src" / "lib"
    if template_lib_dir.exists():
        if not target_lib_dir.exists():
            target_lib_dir.mkdir(parents=True, exist_ok=True)
        for item in template_lib_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_lib_dir / item.name)
        console.print(f"Synced lib to {target_lib_dir}")
    
    for config_file in config_files:
        if config_file == "vite.config.ts":
             # Use template for vite.config.ts
             generate_file("frontend_vite.config.ts.j2", {"config": site_config}, target_frontend_root / config_file)
             continue
             
        src = template_frontend_root / config_file
        dst = target_frontend_root / config_file
        if src.exists():
            # Check if destination exists. If it does, we might be overwriting user changes.
            # But for core infrastructure files in this tool context, we probably want to keep them in sync 
            # or at least update them if they are vastly different.
            # For simplicity in this demo, we'll overwrite to ensure the new stack works.
            # In a real tool, maybe ask for confirmation or only update if missing.
            # But here, we just overwrite to fix the user's issue.
            if dst.parent.exists(): # Ensure parent dir exists (e.g. src/)
                shutil.copy2(src, dst)
                console.print(f"Synced config file: {config_file}")

    # Sync Backend API Endpoints (for upload.py)
    template_endpoints_dir = Path(__file__).parent / "templates" / "backend" / "app" / "api" / "endpoints"
    target_endpoints_dir = backend_path / "app" / "api" / "endpoints"
    
    if template_endpoints_dir.exists():
        if not target_endpoints_dir.exists():
            target_endpoints_dir.mkdir(parents=True, exist_ok=True)
            
        # Use template for upload.py to support dynamic upload dir
        generate_file("backend_api_upload.py.j2", {"config": site_config}, target_endpoints_dir / "upload.py")

        # Copy login.py
        login_py = template_endpoints_dir / "login.py"
        if login_py.exists():
             shutil.copy2(login_py, target_endpoints_dir / "login.py")
             console.print(f"Synced backend endpoint: login.py")

    template_security = Path(__file__).parent / "templates" / "backend" / "app" / "core" / "security.py"
    target_security = backend_path / "app" / "core" / "security.py"
    if template_security.exists():
         shutil.copy2(template_security, target_security)
         console.print(f"Synced backend security.py")

    # Generate config.py from template (using site_config)
    # We use a special template for config.py that accepts site_config
    # If the template file in templates/backend/... is just a static py file, we need to make it a jinja2 template
    # For now, let's assume we create config.py.j2 in templates/codegen/backend_core/
    # But to minimize file movement, let's just use generate_file with a new template name
    # We will create "backend_config.py.j2" in codegen templates
    generate_file("backend_config.py.j2", {"config": site_config}, backend_path / "app" / "core" / "config.py")

    template_db = Path(__file__).parent / "templates" / "backend" / "app" / "core" / "db.py"
    target_db = backend_path / "app" / "core" / "db.py"
    if template_db.exists():
         shutil.copy2(template_db, target_db)
         console.print(f"Synced backend db.py")

    template_deps = Path(__file__).parent / "templates" / "backend" / "app" / "core" / "deps.py"
    target_deps = backend_path / "app" / "core" / "deps.py"
    if template_deps.exists():
         shutil.copy2(template_deps, target_deps)
         console.print(f"Synced backend deps.py")

    template_initial_data = Path(__file__).parent / "templates" / "backend" / "app" / "initial_data.py"
    target_initial_data = backend_path / "app" / "initial_data.py"
    if template_initial_data.exists():
         shutil.copy2(template_initial_data, target_initial_data)
         console.print(f"Synced backend initial_data.py")
     
    # Sync Backend Main (main.py)
    # Use template for main.py to support dynamic upload dir mount
    generate_file("backend_main.py.j2", {"config": site_config}, backend_path / "app" / "main.py")

    # Sync requirements.txt
    template_requirements = Path(__file__).parent / "templates" / "backend" / "requirements.txt"
    target_requirements = backend_path / "requirements.txt"
    if template_requirements.exists():
         shutil.copy2(template_requirements, target_requirements)
         console.print(f"Synced requirements.txt")

    # Sync Backend Dockerfile
    template_backend_dockerfile = Path(__file__).parent / "templates" / "backend" / "Dockerfile"
    target_backend_dockerfile = backend_path / "Dockerfile"
    if template_backend_dockerfile.exists():
         shutil.copy2(template_backend_dockerfile, target_backend_dockerfile)
         console.print(f"Synced backend Dockerfile")

    # Sync Frontend Dockerfile and Nginx Config
    template_frontend_dockerfile = Path(__file__).parent / "templates" / "frontend" / "Dockerfile"
    target_frontend_dockerfile = cwd / "frontend" / "Dockerfile"
    if template_frontend_dockerfile.exists():
         shutil.copy2(template_frontend_dockerfile, target_frontend_dockerfile)
         console.print(f"Synced frontend Dockerfile")
         
    # Use template for nginx.conf to support dynamic upload dir proxy
    generate_file("frontend_nginx.conf.j2", {"config": site_config}, cwd / "frontend" / "nginx.conf")

    # Sync Backend API Router (api.py) - Base template
    template_backend_api = Path(__file__).parent / "templates" / "backend" / "app" / "api" / "api.py"
    target_backend_api = backend_path / "app" / "api" / "api.py"
    if template_backend_api.exists():
         # We copy it first to get the imports for upload, user etc.
         # But wait, update_api_router below will overwrite it?
         # No, update_api_router appends or rewrites.
         # We need to make sure update_api_router preserves the upload router or we handle it there.
         pass 

    # Update api.py to include new routers

    # Filter out link tables for API router inclusion
    api_models = [m for m in found_models if not m["is_link_table"]]
    update_api_router(api_models, backend_path / "app" / "api" / "api.py")
    
    # Update Frontend Routes and Menu
    generate_file("frontend_routes.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Routes.tsx")
    generate_file("frontend_menu.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Menu.tsx")
    
    # Generate i18n locale files
    generate_locale_files(found_models, cwd / "frontend" / "src" / "locales")

def generate_locale_files(models: List[Dict], locale_dir: Path):
    locale_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. English (Default)
    en_translations = {
        "common": {
            "welcome": "Welcome",
            "login": "Login",
            "logout": "Logout",
            "settings": "Settings",
            "language": "Language",
            "timezone": "Timezone",
            "save": "Save",
            "cancel": "Cancel",
            "create": "Create",
            "edit": "Edit",
            "delete": "Delete",
            "actions": "Actions",
            "search": "Search",
            "loading": "Loading...",
            "success": "Success",
            "error": "Error",
            "confirm_delete": "Are you sure you want to delete this item?",
            "upload": "Upload"
        },
        "models": {}
    }
    
    # 2. Chinese (Simplified)
    zh_translations = {
        "common": {
            "welcome": "欢迎",
            "login": "登录",
            "logout": "退出登录",
            "settings": "设置",
            "language": "语言",
            "timezone": "时区",
            "save": "保存",
            "cancel": "取消",
            "create": "创建",
            "edit": "编辑",
            "delete": "删除",
            "actions": "操作",
            "search": "搜索",
            "loading": "加载中...",
            "success": "成功",
            "error": "错误",
            "confirm_delete": "确定要删除此项吗？",
            "upload": "上传"
        },
        "models": {}
    }

    for model in models:
        model_name = model["lower_name"]
        
        # Model Name Translation
        model_name_en = model["name"]
        model_name_zh = model["name"] # Fallback
        
        model_translations = model.get("translations", {})
        if "en" in model_translations:
            model_name_en = model_translations["en"]
        if "zh" in model_translations:
            model_name_zh = model_translations["zh"]
            
        en_model = {"name": model_name_en, "fields": {}}
        zh_model = {"name": model_name_zh, "fields": {}}
        
        for field in model["fields"]:
            field_name = field["name"]
            # Default English label: Title Case of field name
            label_en = field_name.replace("_", " ").title()
            label_zh = label_en # Fallback for ZH
            
            # Use explicit translations if available
            translations = field.get("translations", {})
            if "en" in translations:
                label_en = translations["en"]
            if "zh" in translations:
                label_zh = translations["zh"]
            
            en_model["fields"][field_name] = label_en
            zh_model["fields"][field_name] = label_zh
            
        en_translations["models"][model_name] = en_model
        zh_translations["models"][model_name] = zh_model

    import json
    (locale_dir / "en.json").write_text(json.dumps(en_translations, indent=2))
    (locale_dir / "zh.json").write_text(json.dumps(zh_translations, indent=2, ensure_ascii=False))
    console.print(f"Generated locale files in {locale_dir}")

def update_api_router(models, api_file_path):
    lines = []
    imports = []
    routers = []
    
    # Always include upload router
    imports.append("from app.api.endpoints import upload")
    routers.append("api_router.include_router(upload.router, tags=[\"upload\"])")

    # Always include login router
    imports.append("from app.api.endpoints import login")
    routers.append("api_router.include_router(login.router, tags=[\"login\"])")

    for model in models:
        imports.append(f"from app.api.endpoints import {model['lower_name']}")
        routers.append(f"api_router.include_router({model['lower_name']}.router, prefix=\"/{model['lower_name']}s\", tags=[\"{model['lower_name']}s\"])")
        
    content = "from fastapi import APIRouter\n" + "\n".join(imports) + "\n\napi_router = APIRouter()\n\n" + "\n".join(routers)
    api_file_path.write_text(content)
    console.print(f"Updated {api_file_path}")

import os
import sys
import importlib
import inspect
import pkgutil
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
        
        # Check metadata for search field
        is_search_field = site_props.get("is_search_field", False)
        
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
            "required": field.is_required(),
            "default": field.default,
            "is_enum": is_enum,
            "enum_values": enum_values,
            "is_search_field": is_search_field,
            "fk_info": fk_info
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
    if hasattr(model_cls, "__table_args__") and isinstance(model_cls.__table_args__, dict):
        info = model_cls.__table_args__.get("info", {})
        is_link_table = info.get("site_props", {}).get("is_link_table", False)

    return fields, foreign_keys, search_field, is_link_table

def generate_file(template_name: str, context: Dict, output_path: Path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    content = template.render(context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    console.print(f"Generated {output_path}")

def generate_code():
    # Assume we are in the project root
    cwd = Path(os.getcwd())
    backend_path = cwd / "backend"
    
    if not backend_path.exists():
        console.print("[red]Backend directory not found. Are you in the project root?[/red]")
        return

    # 0. Sync models from root/models to backend/app/models
    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    
    if models_src_dir.exists():
        import shutil
        console.print(f"[green]Syncing models from {models_src_dir} to {models_dest_dir}...[/green]")
        if not models_dest_dir.exists():
            models_dest_dir.mkdir(parents=True, exist_ok=True)
            # Ensure __init__.py exists
            (models_dest_dir / "__init__.py").touch()
            
        for model_file in models_src_dir.glob("*.py"):
            shutil.copy2(model_file, models_dest_dir / model_file.name)
            console.print(f"Synced model: {model_file.name}")
    else:
        console.print(f"[yellow]Models directory not found at {models_src_dir}, skipping model sync.[/yellow]")

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
                     fields, foreign_keys, search_field, is_link_table = get_model_fields(obj)
                     
                     # Special handling for User model to add virtual 'password' field if not present
                     # Moving this logic out of get_model_fields to keep it clean or handle here
                     if name == 'User':
                        has_password = any(f['name'] == 'password' for f in fields)
                        if not has_password:
                             fields.append({
                                 "name": "password",
                                 "type": "str",
                                 "ui_type": "str",
                                 "permissions": "c", # Only for creation
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
                         "is_link_table": is_link_table
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
        import shutil
        shutil.copy2(pagination_schema_src, pagination_schema_dst)
        console.print(f"Synced pagination schema to {pagination_schema_dst}")

    # Generate code for each model
    for model in found_models:
        # Skip generating views/APIs for link tables
        if model["is_link_table"]:
            continue
            
        context = {"model": model}
        
        # 1. Schemas
        generate_file("schema.py.j2", context, backend_path / "app" / "schemas" / f"{model['lower_name']}.py")
        
        # 2. CRUD
        generate_file("crud.py.j2", context, backend_path / "app" / "cruds" / f"{model['lower_name']}.py")
        
        # 3. Service
        generate_file("service.py.j2", context, backend_path / "app" / "services" / f"{model['lower_name']}.py")
        
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
    import shutil
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
    template_utils_dir = Path(__file__).parent / "templates" / "frontend" / "src" / "lib"
    target_utils_dir = cwd / "frontend" / "src" / "lib"
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
        "src/components/Layout.tsx",
        "src/utils/request.ts"
    ]
    template_frontend_root = Path(__file__).parent / "templates" / "frontend"
    target_frontend_root = cwd / "frontend"
    
    for config_file in config_files:
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

    # Update api.py to include new routers
    # Filter out link tables for API router inclusion
    api_models = [m for m in found_models if not m["is_link_table"]]
    update_api_router(api_models, backend_path / "app" / "api" / "api.py")
    
    # Update Frontend Routes and Menu
    generate_file("frontend_routes.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Routes.tsx")
    generate_file("frontend_menu.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Menu.tsx")

def update_api_router(models, api_file_path):
    lines = []
    imports = []
    routers = []
    
    for model in models:
        imports.append(f"from app.api.endpoints import {model['lower_name']}")
        routers.append(f"api_router.include_router({model['lower_name']}.router, prefix=\"/{model['lower_name']}s\", tags=[\"{model['lower_name']}s\"])")
        
    content = "from fastapi import APIRouter\n" + "\n".join(imports) + "\n\napi_router = APIRouter()\n\n" + "\n".join(routers)
    api_file_path.write_text(content)
    console.print(f"Updated {api_file_path}")

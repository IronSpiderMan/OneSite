import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from app.cruds import product as crud
from app.schemas.product import ProductCreate, ProductUpdate, ProductTagMeta
from app.schemas.pagination import PaginatedResponse
from app.schemas.product import ProductRead


from app.schemas.tag import TagRead





logger = logging.getLogger(__name__)

class ProductService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[ProductRead]:
        obj = await crud.get(session, id)
        return ProductRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        name: Optional[str] = None,
        
        
        
        
        
        status: Optional[str] = None,
        
        
        
        
        
        is_featured: Optional[bool] = None,
        
        
        
        
        
        
        
        
        
        
        
        created_at_from: Optional[datetime] = None,
        created_at_to: Optional[datetime] = None,
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        category_id: Optional[int] = None,
        
        
        
    ) -> PaginatedResponse[ProductRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            name=name,
            
            
            
            
            
            status=status,
            
            
            
            
            
            is_featured=is_featured,
            
            
            
            
            
            
            
            
            
            
            
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            
            
            
            
            
            
            
            
            
            
            
            
            
            category_id=category_id,
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            name=name,
            
            
            
            
            
            status=status,
            
            
            
            
            
            is_featured=is_featured,
            
            
            
            
            
            
            
            
            
            
            
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            
            
            
            
            
            
            
            
            
            
            
            
            
            category_id=category_id,
            
            
            
        )

        # Build response
        items_read = [ProductRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: ProductCreate) -> ProductRead:
        
        
        obj = await crud.create(session, obj_in)

        

        
        return ProductRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: ProductUpdate) -> ProductRead:
        """
        Update Product by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Product not found")
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return ProductRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    
    # M2M Relationship methods
    
    async def get_tags(
        self,
        session: AsyncSession,
        product_id: int,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[TagRead]:
        """
        Get Tags related to Product.
        """
        # Get total count
        total = await crud.count_tags(session, product_id)

        if total == 0:
            return PaginatedResponse.create(data=[], total=0, page=page, size=size)

        # Get items (CRUD returns objects directly with pagination)
        items = await crud.get_tags(session, product_id, page=page, size=size)

        # Convert to ReadSchema
        items_read = [TagRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    
    async def get_tags_with_meta(
        self,
        session: AsyncSession,
        product_id: int,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedResponse[ProductTagMeta]:
        """
        Get Tags related to Product with link-table order.
        """
        # Count total first
        total = await crud.count_tags(session, product_id)

        if total == 0:
            return PaginatedResponse.create(data=[], total=0, page=page, size=size)

        # Get all if size == -1
        if size == -1:
            rows, _ = await crud.get_tags_with_order(session, product_id, page=1, size=total)
            items = [
                ProductTagMeta(id=r[0], label=str(r[1]), order=int(r[2] or 0))
                for r in rows
            ]
            return PaginatedResponse.create(data=items, total=total, page=1, size=total)

        rows, _ = await crud.get_tags_with_order(session, product_id, page, size)

        items = [
            ProductTagMeta(id=r[0], label=str(r[1]), order=int(r[2] or 0))
            for r in rows
        ]

        return PaginatedResponse.create(data=items, total=total, page=page, size=size)
    
    
    

    

    

    
    # Import/Export methods
    
    async def export_to_csv(
        self,
        session: AsyncSession,
        *,
        task_id: str,
        user_id: int,
        filters: Optional[dict] = None,
        ws_manager = None,
    ) -> str:
        """
        Export Product records to CSV.
        Returns the file path of the exported CSV.
        Foreign key fields are exported as labels (not IDs).
        """
        import csv
        import os
        from datetime import datetime
        from sqlmodel import select
        
        upload_dir = os.environ.get("UPLOAD_DIR", "uploads")
        export_dir = os.path.join(upload_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"product_export_{timestamp}.csv"
        filepath = os.path.join(export_dir, filename)

        # Write CSV with UTF-8 BOM for Excel compatibility
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # Header - exclude id, created_at, updated_at for clean import/export cycle
            headers = ["name", "status", "is_featured", "category_id", "variants", "meta_data", "cover_image", "manual_file", "internal_note"]
            writer.writerow(headers)
            
            
            # Build FK label caches
            
            category_id_label_cache = {}
            
            
            
            # Process in batches
            batch_size = 1000
            page = 1
            
            while True:
                items = await crud.get_multi(session, page=page, size=batch_size)
                if not items:
                    break
                
                
                # Collect unique FK IDs for batch label resolution
                
                category_id_ids = list(set(
                    getattr(item, "category_id") for item in items 
                    if getattr(item, "category_id") is not None 
                    and getattr(item, "category_id") not in category_id_label_cache
                ))
                
                
                # Batch fetch FK labels
                
                if category_id_ids:
                    from app.models.category import Category
                    stmt = select(Category).where(Category.id.in_(category_id_ids))
                    result = await session.exec(stmt)
                    for obj in result.all():
                        category_id_label_cache[obj.id] = getattr(obj, "name", None) or str(obj.id)
                
                
                
                for item in items:
                    row = []
                    
                    
                    
                    
                    
                    val = getattr(item, "name", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    val = getattr(item, "status", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    val = getattr(item, "is_featured", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    # FK field - export label instead of ID
                    fk_id = getattr(item, "category_id", None)
                    if fk_id is None:
                        row.append("")
                    elif fk_id in category_id_label_cache:
                        row.append(category_id_label_cache[fk_id])
                    else:
                        row.append(str(fk_id))
                    
                    
                    
                    
                    
                    val = getattr(item, "variants", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    val = getattr(item, "meta_data", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    
                    
                    val = getattr(item, "cover_image", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    val = getattr(item, "manual_file", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    
                    
                    
                    
                    val = getattr(item, "internal_note", None)
                    # Convert to string, handle Enum/datetime specially
                    if val is None:
                        row.append("")
                    elif hasattr(val, 'value'):
                        # Enum type - get the value
                        row.append(str(val.value))
                    elif hasattr(val, 'isoformat'):
                        # datetime type - use ISO format
                        row.append(val.isoformat())
                    else:
                        row.append(str(val))
                    
                    
                    
                    writer.writerow(row)
                
                page += 1
                
                if len(items) < batch_size:
                    break
        
        return filepath
    

    
    async def import_from_csv(
        self,
        session: AsyncSession,
        *,
        task_id: str,
        user_id: int,
        file: Any,
        dry_run: bool = False,
        ws_manager = None,
    ) -> dict:
        """
        Import Product records from CSV.
        Uses upsert logic: if record with same name exists, update it; otherwise create new.
        Foreign key fields in CSV should be labels (not IDs), and will be resolved to IDs.
        """
        import csv
        import io
        import json
        import ast
        from datetime import datetime
        from sqlmodel import select

        contents = await file.read()
        csv_file = io.StringIO(contents.decode('utf-8-sig'))
        reader = csv.DictReader(csv_file)

        rows = list(reader)

        stats = {"success": 0, "failed": 0, "created": 0, "updated": 0, "errors": []}
        import_key = "name"

        
        # Build FK label-to-ID caches
        
        category_id_cache = {}
        
        
        # Pre-fetch all FK targets for label resolution
        
        from app.models.category import Category as Category_model
        stmt = select(Category_model)
        result = await session.exec(stmt)
        for obj in result.all():
            label = getattr(obj, "name", None) or str(obj.id)
            category_id_cache[label] = obj.id
            category_id_cache[str(obj.id)] = obj.id  # Also allow ID as fallback
        
        

        for idx, row in enumerate(rows, 1):
            try:
                # Get the unique field value
                key_value = row.get(import_key)
                if not key_value:
                    stats["failed"] += 1
                    stats["errors"].append(f"Row {idx}: Missing import key '{import_key}'")
                    continue

                # Check if record exists
                existing = await crud.get_by_name(session, key_value)
                is_update = existing is not None

                # Build data object from row
                obj_data = {}
                
                
                
                
                
                if "name" in row:
                    value = row["name"]
                    
                    obj_data["name"] = value
                    
                
                
                
                
                
                if "status" in row:
                    value = row["status"]
                    
                    obj_data["status"] = value
                    
                
                
                
                
                
                if "is_featured" in row:
                    value = row["is_featured"]
                    
                    obj_data["is_featured"] = value.lower() in ('true', '1', 'yes', 'on') if value else False
                    
                
                
                
                
                
                if "category_id" in row:
                    value = row["category_id"]
                    
                    # FK field - resolve label to ID
                    if not value:
                        obj_data["category_id"] = None
                    elif value in category_id_cache:
                        obj_data["category_id"] = category_id_cache[value]
                    else:
                        # Try to find by searching
                        from app.models.category import Category as Category_import
                        stmt = select(Category_import).where(
                            getattr(Category_import, "name") == value
                        )
                        fk_result = await session.exec(stmt)
                        fk_obj = fk_result.first()
                        if fk_obj:
                            obj_data["category_id"] = fk_obj.id
                            category_id_cache[value] = fk_obj.id
                        else:
                            raise ValueError(f"Foreign key '{value}' not found for field 'category_id'")
                    
                
                
                
                
                
                if "variants" in row:
                    value = row["variants"]
                    
                    obj_data["variants"] = ast.literal_eval(value) if value else []
                    
                
                
                
                
                
                if "meta_data" in row:
                    value = row["meta_data"]
                    
                    obj_data["meta_data"] = ast.literal_eval(value) if value else []
                    
                
                
                
                
                
                
                
                if "cover_image" in row:
                    value = row["cover_image"]
                    
                    obj_data["cover_image"] = value
                    
                
                
                
                
                
                if "manual_file" in row:
                    value = row["manual_file"]
                    
                    obj_data["manual_file"] = value
                    
                
                
                
                
                
                if "import_source" in row:
                    value = row["import_source"]
                    
                    obj_data["import_source"] = value
                    
                
                
                
                
                
                if "internal_note" in row:
                    value = row["internal_note"]
                    
                    obj_data["internal_note"] = value
                    
                
                
                

                if not dry_run:
                    if is_update:
                        # Update existing record (updated_at auto-set in update method)
                        obj_in = ProductUpdate(**obj_data)
                        await self.update(session, existing.id, obj_in)
                        stats["updated"] += 1
                    else:
                        # Create new record (created_at and updated_at auto-set in create method)
                        obj_in = ProductCreate(**obj_data)
                        await self.create(session, obj_in)
                        stats["created"] += 1

                stats["success"] += 1

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"Row {idx}: {str(e)}")

        return stats
    
    

    


service = ProductService()
import logging
from typing import Optional, Any
from datetime import datetime, timezone
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.book import Book
from app.cruds import book as crud
from app.schemas.book import BookCreate, BookUpdate
from app.schemas.pagination import PaginatedResponse
from app.schemas.book import BookRead


from app.schemas.subject import SubjectRead





logger = logging.getLogger(__name__)

class BookService:
    

    async def get(self, session: AsyncSession, id: int) -> Optional[BookRead]:
        obj = await crud.get(session, id)
        return BookRead.model_validate(obj) if obj else None

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        
        
        
        
        
        title: Optional[str] = None,
        
        
        
        
        
        published_at_from: Optional[datetime] = None,
        published_at_to: Optional[datetime] = None,
        
        
        
        
        
        
        
        
        author_id: Optional[int] = None,
        
        
        
    ) -> PaginatedResponse[BookRead]:
        """
        Get paginated list with optional search and filter support.
        Combines CRUD get_multi and count into PaginatedResponse.
        """
        # Get total count first
        total = await crud.count(
            session,
            
            
            
            
            
            title=title,
            
            
            
            
            
            published_at_from=published_at_from,
            published_at_to=published_at_to,
            
            
            
            
            
            
            
            author_id=author_id,
            
            
            
        )

        # Get items with FK labels
        items = await crud.get_multi_with_fk_labels(
            session,
            page=page,
            size=size,
            
            
            
            
            
            title=title,
            
            
            
            
            
            published_at_from=published_at_from,
            published_at_to=published_at_to,
            
            
            
            
            
            
            
            author_id=author_id,
            
            
            
        )

        # Build response
        items_read = [BookRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    async def create(self, session: AsyncSession, obj_in: BookCreate) -> BookRead:
        
        # Check unique field constraints
        
        
        
        
        if getattr(obj_in, "title", None) is not None:
            if not await crud.check_unique_field(session, "title", obj_in.title):
                raise ValueError("title already exists")
        
        
        
        
        
        
        
        
        obj = await crud.create(session, obj_in)

        

        
        return BookRead.model_validate(obj)

    async def update(self, session: AsyncSession, id: int, obj_in: BookUpdate) -> BookRead:
        """
        Update Book by ID with validation.
        Raises ValueError if unique constraint is violated.
        Raises NotFoundError if object doesn't exist.
        """
        db_obj = await crud.get(session, id)
        if not db_obj:
            raise ValueError("Book not found")
        
        
        # Check unique field constraints (only for fields being updated)
        
        
        
        
        if getattr(obj_in, "title", None) is not None and getattr(obj_in, "title") != getattr(db_obj, "title"):
            if not await crud.check_unique_field(session, "title", obj_in.title, exclude_id=id):
                raise ValueError("title already exists")
        
        
        
        
        
        
        

        obj = await crud.update(session, db_obj, obj_in)

        

        
        return BookRead.model_validate(obj)

    async def delete(self, session: AsyncSession, id: int) -> int:
        return await crud.delete(session, id)

    

    
    # M2M Relationship methods
    
    async def get_subjects(
        self,
        session: AsyncSession,
        book_id: int,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[SubjectRead]:
        """
        Get Subjects related to Book.
        """
        # Get total count
        total = await crud.count_subjects(session, book_id)

        if total == 0:
            return PaginatedResponse.create(data=[], total=0, page=page, size=size)

        # Get items (CRUD returns objects directly with pagination)
        items = await crud.get_subjects(session, book_id, page=page, size=size)

        # Convert to ReadSchema
        items_read = [SubjectRead.model_validate(item) for item in items]
        if size == -1:
            return PaginatedResponse.create(data=items_read, total=total, page=1, size=total)
        return PaginatedResponse.create(data=items_read, total=total, page=page, size=size)

    
    
    

    

    

    
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
        Export Book records to CSV.
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
        filename = f"book_export_{timestamp}.csv"
        filepath = os.path.join(export_dir, filename)

        # Write CSV with UTF-8 BOM for Excel compatibility
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # Header - exclude id, created_at, updated_at for clean import/export cycle
            headers = ["title", "published_at", "author_id"]
            writer.writerow(headers)
            
            
            # Build FK label caches
            
            author_id_label_cache = {}
            
            
            
            # Process in batches
            batch_size = 1000
            page = 1
            
            while True:
                items = await crud.get_multi(session, page=page, size=batch_size)
                if not items:
                    break
                
                
                # Collect unique FK IDs for batch label resolution
                
                author_id_ids = list(set(
                    getattr(item, "author_id") for item in items 
                    if getattr(item, "author_id") is not None 
                    and getattr(item, "author_id") not in author_id_label_cache
                ))
                
                
                # Batch fetch FK labels
                
                if author_id_ids:
                    from app.models.author import Author
                    stmt = select(Author).where(Author.id.in_(author_id_ids))
                    result = await session.exec(stmt)
                    for obj in result.all():
                        author_id_label_cache[obj.id] = getattr(obj, "name", None) or str(obj.id)
                
                
                
                for item in items:
                    row = []
                    
                    
                    
                    
                    
                    val = getattr(item, "title", None)
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
                    
                    
                    
                    
                    
                    val = getattr(item, "published_at", None)
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
                    fk_id = getattr(item, "author_id", None)
                    if fk_id is None:
                        row.append("")
                    elif fk_id in author_id_label_cache:
                        row.append(author_id_label_cache[fk_id])
                    else:
                        row.append(str(fk_id))
                    
                    
                    
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
        Import Book records from CSV.
        Uses upsert logic: if record with same title exists, update it; otherwise create new.
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
        import_key = "title"

        
        # Build FK label-to-ID caches
        
        author_id_cache = {}
        
        
        # Pre-fetch all FK targets for label resolution
        
        from app.models.author import Author as Author_model
        stmt = select(Author_model)
        result = await session.exec(stmt)
        for obj in result.all():
            label = getattr(obj, "name", None) or str(obj.id)
            author_id_cache[label] = obj.id
            author_id_cache[str(obj.id)] = obj.id  # Also allow ID as fallback
        
        

        for idx, row in enumerate(rows, 1):
            try:
                # Get the unique field value
                key_value = row.get(import_key)
                if not key_value:
                    stats["failed"] += 1
                    stats["errors"].append(f"Row {idx}: Missing import key '{import_key}'")
                    continue

                # Check if record exists
                existing = await crud.get_by_title(session, key_value)
                is_update = existing is not None

                # Build data object from row
                obj_data = {}
                
                
                
                
                
                if "title" in row:
                    value = row["title"]
                    
                    obj_data["title"] = value
                    
                
                
                
                
                
                
                
                if "author_id" in row:
                    value = row["author_id"]
                    
                    # FK field - resolve label to ID
                    if not value:
                        obj_data["author_id"] = None
                    elif value in author_id_cache:
                        obj_data["author_id"] = author_id_cache[value]
                    else:
                        # Try to find by searching
                        from app.models.author import Author as Author_import
                        stmt = select(Author_import).where(
                            getattr(Author_import, "name") == value
                        )
                        fk_result = await session.exec(stmt)
                        fk_obj = fk_result.first()
                        if fk_obj:
                            obj_data["author_id"] = fk_obj.id
                            author_id_cache[value] = fk_obj.id
                        else:
                            raise ValueError(f"Foreign key '{value}' not found for field 'author_id'")
                    
                
                
                

                if not dry_run:
                    if is_update:
                        # Update existing record (updated_at auto-set in update method)
                        obj_in = BookUpdate(**obj_data)
                        await self.update(session, existing.id, obj_in)
                        stats["updated"] += 1
                    else:
                        # Create new record (created_at and updated_at auto-set in create method)
                        obj_in = BookCreate(**obj_data)
                        await self.create(session, obj_in)
                        stats["created"] += 1

                stats["success"] += 1

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"Row {idx}: {str(e)}")

        return stats
    
    

    


service = BookService()
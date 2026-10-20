# Private file fields

Use `component="file"` with `private=True` in a SQLModel field's `site_props`:

```python
key_path: str | None = Field(default=None, sa_column_kwargs={
    "info": {"site_props": {"component": "file", "private": True}}
})
```

Private uploads require an authenticated account and are not supported during anonymous registration.

Run `site sync` to regenerate the API and file editors. Existing public file fields are unchanged.

Private fields upload through `POST /api/v1/upload/private/{model}/{field}`. The authenticated role must hold matching create or update permission on both the model and field. The target must be declared as a private file field. CRUD record permissions still govern attaching the returned reference to a record.

Files are stored outside public static directories in `PRIVATE_UPLOAD_DIR` (default `private_uploads`), with random names and file permissions 0600. The default server upload limit is 20 MiB (`PRIVATE_UPLOAD_MAX_BYTES`). Empty and oversized uploads are rejected and partial files removed. The private directory cannot be inside public uploads or static storage. Do not expose it through a reverse proxy or a custom StaticFiles mount.

The stored `/private-uploads/<random-name>` value is an opaque reference, **not a browser download URL**. Private files are upload-only: no preview/download API is provided and private file components disable both actions regardless of `allow_download`. Trusted backend consumers resolve the reference against the configured private directory; other services may consume a read-only mounted directory. Deployments must persist that directory separately from public uploads and mount it read-only for consumers.

Files removed from a field or abandoned before saving are not automatically deleted. Deployment owners must handle retention; deleting a shared file on an arbitrary field change could break another record. This feature does not encrypt files at rest or make database/file-system administrators unable to read them.

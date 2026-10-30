# Storage & Project Persistence

## 1. Storage Architecture

MayaChitram separates relational metadata from binary media asset storage:

```text
┌─────────────────────────┐          ┌─────────────────────────┐
│     SQLite Database     │          │    Managed File Store   │
│  (data/mayachitram.db)  │          │      (data/storage/)    │
├─────────────────────────┤          ├─────────────────────────┤
│ projects                │          │ projects/               │
│ assets                  │◄────────►│   {project_id}/         │
│ operations              │          │     {uuid}.png          │
│ schema_migrations       │          │     {uuid}.webp         │
└─────────────────────────┘          └─────────────────────────┘
```

---

## 2. Relational Schema

### `projects` Table
- `id` (TEXT, Primary Key): UUID v4
- `name` (TEXT, Not Null): Human-readable project name
- `description` (TEXT): Optional project notes
- `settings` (TEXT, Not Null): JSON settings dictionary
- `created_at` (TEXT, Not Null): ISO 8601 UTC timestamp
- `updated_at` (TEXT, Not Null): ISO 8601 UTC timestamp

### `assets` Table
- `id` (TEXT, Primary Key): UUID v4
- `project_id` (TEXT, Foreign Key -> `projects.id` ON DELETE CASCADE)
- `original_filename` (TEXT, Not Null): User or tool-assigned filename
- `media_type` (TEXT, Not Null): MIME type (`image/png`, `image/jpeg`, `image/webp`)
- `storage_key` (TEXT, Not Null): Relative storage path (`projects/{project_id}/{uuid}.{ext}`)
- `file_size` (INTEGER, Not Null): Size in bytes
- `width` (INTEGER, Not Null): Image pixel width
- `height` (INTEGER, Not Null): Image pixel height
- `parent_asset_id` (TEXT, Foreign Key -> `assets.id` ON DELETE SET NULL): Version lineage
- `metadata` (TEXT, Not Null): JSON metadata (operation ID, generation tool, etc.)
- `created_at` (TEXT, Not Null): ISO 8601 UTC timestamp

### `operations` Table
- `id` (TEXT, Primary Key): UUID v4
- `project_id` (TEXT, Foreign Key -> `projects.id` ON DELETE CASCADE)
- `tool_name` (TEXT, Not Null): Registered tool name (e.g., `image.crop`)
- `parameters` (TEXT, Not Null): JSON dictionary of validated parameters
- `input_asset_ids` (TEXT, Not Null): JSON array of input asset IDs
- `output_asset_ids` (TEXT, Not Null): JSON array of output asset IDs
- `status` (TEXT, Not Null): `pending` | `running` | `succeeded` | `failed`
- `error` (TEXT): Error message if status is `failed`
- `created_at` (TEXT, Not Null): ISO 8601 UTC timestamp
- `completed_at` (TEXT): ISO 8601 UTC timestamp

---

## 3. Security & Safe Storage

- **Path Traversal Protection:** The storage service enforces that all resolved filesystem paths reside strictly inside the managed storage root directory. Any attempt to reference `../` or absolute OS paths raises a `StorageError`.
- **Randomized File Keys:** User filenames are never used as disk filenames. Storage keys use random UUIDs (`{uuid}.{ext}`).
- **Cascade Deletion:** Deleting a project automatically deletes all related database records and purges all associated media files from storage.

---

## 4. Portability & Future Cloud Migration

The `StorageService` protocol defines:
- `save(data: bytes, extension: str, prefix: str) -> str`
- `read(storage_key: str) -> bytes`
- `delete(storage_key: str) -> bool`
- `exists(storage_key: str) -> bool`
- `get_absolute_path(storage_key: str) -> Path`

To migrate to AWS S3, Google Cloud Storage, or Azure Blob Storage, implement the `StorageService` interface without changing a single line of business logic in `ImageEngine` or `ExecutionService`.

# Security Architecture & Policy

## 1. Threat Model & Mitigations

### 1.1 Secret Protection (Groq API Key)
- `GROQ_API_KEY` is loaded strictly on the server through `mayachitram.core.config.Settings`.
- Never included in frontend bundles, Vite environment variables, or HTML outputs.
- `.env` files are ignored in `.gitignore`.

### 1.2 Resource Exhaustion & Image Bombs
- **Decompression Bombs:** Pillow limits max pixels to `50,000,000` via `Image.MAX_IMAGE_PIXELS`. Images exceeding this limit are rejected before decompression.
- **Dimension Caps:** Max width and height are bounded at `8,192` pixels (`MAX_IMAGE_DIMENSION`).
- **File Size Caps:** Upload endpoints enforce `MAX_UPLOAD_BYTES` (default 20MB) at stream read time, returning HTTP 413 if exceeded.

### 1.3 Path Traversal Prevention
- `LocalStorageService` strictly resolves and normalizes every storage key:
  ```python
  target_path = (self.root_dir / cleaned_key).resolve()
  target_path.relative_to(self.root_dir)  # Raises StorageError on traversal
  ```
- User-supplied filenames are never used as on-disk filesystem paths. Files are stored using random UUIDs.

### 1.4 AI Sandboxing & Tool Safety
- Maya has no access to `eval()`, `exec()`, `os.system()`, raw SQL queries, or arbitrary URLs.
- The planner can only request tools present in the statically registered `ToolRegistry`.
- Every tool parameter is validated through strict Pydantic schemas before execution.

### 1.5 Authentication Notice
This version is designed as a local single-user creative studio platform. Multi-tenant authentication (OAuth2 / JWT) and access control lists must be introduced before multi-tenant public deployment.

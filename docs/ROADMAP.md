# MayaChitram Product Roadmap

## Implemented Stages

### Stage 0 — Reliable Foundation (COMPLETED)
- Stabilized FastAPI service, centralized settings, and consistent API error schemas.
- Content validation: format verification, dimension bounds, pixel limits (`MAX_IMAGE_PIXELS = 50,000,000`).
- Deterministic Pillow processing engine with standalone endpoint (`POST /api/v1/image/process`).
- Automated tests verifying image processing and error handling.

### Stage 1 — Image Creator / Image Studio (COMPLETED)
- Dark-first creative workspace with canvas, aspect presets (1:1, 4:5, 16:9, 9:16), before/after comparison toggle, and metadata pills.
- 11 core creative operations implemented and verified:
  1. `image.resize` (explicit width/height, preserve aspect ratio, contain/cover/stretch)
  2. Aspect-preserving resize with social-media presets
  3. `image.crop` (bounding box with coordinate validation)
  4. `image.rotate` (90°, 180°, custom angles, canvas expansion)
  5. `image.flip` (horizontal and vertical flipping)
  6. `image.convert_format` (WebP, JPEG, PNG)
  7. `image.compress` (quality/lossy control 1-100%)
  8. `image.adjust_brightness` (Pillow ImageEnhance)
  9. `image.adjust_contrast` (Pillow ImageEnhance)
  10. `image.adjust_saturation` (grayscale to vibrant)
  11. `image.adjust_temperature` (mathematical RGB warm/cool channel balancing)
- Transparent PNG to JPEG conversion with white background composite (no alpha crash).
- Direct file download and export.

### Stage 2 — Unified Project & Asset Management (COMPLETED)
- Persistent SQLite schema with WAL mode and foreign keys (`projects`, `assets`, `operations`).
- `LocalStorageService` with strict path traversal security.
- Asset version lineage (`parent_asset_id`) for non-destructive editing and version branching.
- Operation history recording input assets, output assets, validated parameters, timestamps, and status.
- Survives full server restarts with project assets and history intact.

### Stage 3 — Maya v1: Conversational AI Creative Assistant (COMPLETED)
- Shared `ToolRegistry` exposing identical tools to manual controls and AI planner.
- Natural-language planning via Groq API (`llama-3.3-70b-versatile`) with structured JSON schema.
- Resilient semantic fallback planner for offline/unconfigured environments.
- Execution service with multi-step output chaining and safety validation.
- Interactive Maya panel in the frontend with plan preview, step rationale, and live progress.

---

## Future Roadmap

### Stage 4 — Advanced AI Vision & Masking
- Background removal (`rembg` or provider API).
- Object segmentation & smart auto-crop.
- Depth map estimation.

### Stage 5 — Multi-Engine Expansion
- `video.*` engine: trimming, concatenation, subtitles, transcoding via FFmpeg.
- `audio.*` engine: noise reduction, normalization, voice transcription.
- `vfx.*` engine: composite layers, blend modes, alpha matting.
- `scene3d.*` engine: glTF model preview, camera positioning, render passes.

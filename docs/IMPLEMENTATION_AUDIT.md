# MayaChitram — Implementation Audit & Baseline Assessment

**Date:** 2026-10-25  
**Auditor:** Principal Software Architect & AI Systems Engineer  
**Repository:** `mayachitram`

---

## 1. Executive Summary

MayaChitram was conceived as an extensible AI-powered creative platform with a long-term vision spanning image editing, audio, video, VFX, and 3D workflows. The starting codebase contained a minimal prototype: a single-route FastAPI service calling Groq Vision inference for scene descriptions, and a single-component React frontend. There were zero image editing operations, zero persistent project storage, and no AI planning assistant.

This audit establishes the baseline facts of the codebase prior to upgrading it in place into a production-grade Image Studio with persistent projects, unified tool registry, and Maya v1 conversational creative assistant.

---

## 2. Baseline Status Audit

### 2.1 What Currently Works
- **FastAPI Infrastructure:** `FastAPI` instance in `mayachitram.main` boots correctly with CORS middleware, `/health` route returning `{"status": "ok", "service": "mayachitram-api"}`, and `/api/v1/engines` returning the registered engines.
- **Image Content Validation (Basic):** `ImageEngine.analyze()` performs PIL format verification (`Image.open`, `image.verify()`), enforcing allowed formats (`JPEG`, `PNG`, `WEBP`) and maximum upload size limits.
- **Groq Vision Provider:** Server-side `GroqVisionProvider` constructs base64 data URIs and calls the Groq chat completions API with `response_format={"type": "json_object"}`. `GROQ_API_KEY` is kept server-side.
- **Frontend Presentation:** Dark-first UI design system (`global.css`) with styling for hero graphics, brand marks, dropzones, badges, and status indicators.
- **Frontend Image Upload Dropzone:** Drag-and-drop and file input handling with client-side MIME and size checks, generating an ephemeral preview via `URL.createObjectURL()`.

### 2.2 What Is Incomplete
- **No Image Processing Tools:** Despite the product purpose being a creative studio, neither backend nor frontend had any image processing functionality: no resize, aspect-ratio preservation, cropping, rotation, flipping, format conversion, compression, or brightness/contrast/saturation adjustments.
- **No Non-Destructive Editing / Undo:** There was no history, versioning, or non-destructive operation records.
- **No Project & Asset Persistence:** Projects, assets, and operation history were completely absent. Uploaded files were analyzed purely in-memory and discarded upon response completion.
- **No Maya Creative Assistant:** There was no natural-language planner, execution engine, or safety validation for creative commands.
- **Provider Capabilities Unaligned:** The default model in `config.py` was set to `qwen/qwen3.8-27b` without fallback or capability validation.

### 2.3 What Was Broken (And Baseline Fixes Applied)
- **Backend Test Runner Pythonpath:** Running `pytest` directly in `backend` failed with `ModuleNotFoundError: No module named 'mayachitram'` because the package was linked to an obsolete build directory and `pyproject.toml` did not configure `pythonpath = ["src"]`. (Resolved: updated `pyproject.toml` and re-installed editable package).
- **Frontend TypeScript Build Failure:** `npm run build` failed with two distinct compiler errors:
  1. `Property 'env' does not exist on type 'ImportMeta'` in `src/services/api.ts` due to missing Vite client types definition. (Resolved: added `src/vite-env.d.ts`).
  2. `No overload matches this call` in `vite.config.ts` due to type incompatibilities between Vitest's bundled Vite 5 types and Vite 6. (Resolved: refined type annotation in `vite.config.ts`).

### 2.4 Security Risks Identified
- **Unbounded Image Decompression (Decompression Bombs):** No guardrails against PIL decompression bombs (`Image.MAX_IMAGE_PIXELS` or dimension limits) on uploaded images.
- **Alpha Channel Drop on Conversion:** Converting transparent PNGs to JPEG without flattening against a background color causes PIL exceptions or corrupted artifacts.
- **Local File Serving & Traversal:** Without an explicit storage abstraction and validation, future asset endpoints could be vulnerable to directory traversal if filenames are trusted as disk paths.
- **Memory Consumption:** Loading large original files repeatedly into memory without managed output keys or streaming could exhaust server resources under concurrent load.
- **Client Key Exposure Prevention:** Verified that `GROQ_API_KEY` is not present in frontend code or Vite environment templates; must remain strictly server-side.

### 2.5 Architectural Problems
- **Monolithic Component Structure:** The entire frontend resided in a single 126-line `App.tsx` file containing brand, hero, engine listing, dropzone, and analysis states. No feature separation or state management.
- **Coupling of Route and Engine:** The existing image route directly coupled file upload to Groq vision analysis without an intermediate execution, asset, or storage abstraction.
- **Lack of Tool Unification:** Manual UI controls and prospective AI controls had no common tool registry or typed invocation interface.

### 2.6 Missing Tests
- Zero tests for image operations (resize, crop, rotate, flip, format conversion, adjustments).
- Zero tests for project lifecycle (create, list, get, update, delete).
- Zero tests for asset persistence, version lineage, and storage cleanup.
- Zero tests for tool registry validation and execution.
- Zero tests for Maya natural-language planning and safety controls.
- Zero UI integration tests for editing controls, before/after previews, and downloads.

---

## 3. Existing Modules Worth Preserving

| Module | Location | Value / Reason to Preserve |
|---|---|---|
| Platform Engine Registry | `backend/src/mayachitram/platform/registry.py` | Clean metadata pattern for discoverable engines. |
| Settings & Config | `backend/src/mayachitram/core/config.py` | Pydantic-settings base with environment prefix `MAYACHITRAM_`. |
| Error Hierarchy | `backend/src/mayachitram/core/errors.py` | Established domain exceptions to extend for studio operations. |
| Groq Vision Provider | `backend/src/mayachitram/engines/image/providers/groq_vision.py` | Functional Groq client structure for vision queries. |
| Visual Styling & Design System | `frontend/src/styles/global.css` | High-quality dark creative visual aesthetic and brand tokens. |

---

## 4. Dependencies & Configuration Review

- **Backend:**
  - Python 3.12+
  - `fastapi`, `uvicorn`, `pydantic-settings`, `python-multipart`, `Pillow`, `groq`, `httpx`, `pytest`, `ruff`.
  - Database: SQLite (standard library `sqlite3` / SQLAlchemy-compatible abstraction) to be added for persistent projects without external service overhead.
- **Frontend:**
  - Node 20+, React 18, Vite 6, TypeScript 5.7, Vitest 2.1, Testing Library.
  - No bloated dependencies needed; lightweight, standard browser Canvas/DOM APIs and native reactive patterns are ideal for rapid, reliable rendering.

---

## 5. Prioritized Implementation Plan

1. **Stage 0 — Reliable Foundation:**
   - Centralize error handling and HTTP status mappings.
   - Implement secure image validation (dimensions, pixel limit, content type detection).
   - Build Image Engine core processing service with a deterministic operation (resize/format).
   - Verify complete upload → process → preview → download cycle with automated tests.
2. **Stage 1 — Image Creator / Studio:**
   - Implement all 11 core editing operations: resize, aspect-preserving resize, crop with coordinates, rotate (90/180/270/custom), flip H/V, format conversion (JPEG, PNG, WebP), compression/quality, brightness, contrast, saturation, and color temperature.
   - Build dark-first creative workspace with canvas, presets (Square 1:1, Portrait 4:5, Landscape 16:9, etc.), before/after comparison, parameter sliders, non-destructive version history, and download/export.
3. **Stage 2 — Unified Project & Asset Management:**
   - Implement SQLite persistence layer (`Project`, `Asset`, `Operation` models).
   - Managed storage service constraining files to configurable data directory with safe UUID-based storage keys.
   - Project and asset management endpoints with cascade cleanup, version lineage, and pagination.
4. **Stage 3 — Shared Tool Registry & Maya v1 Assistant:**
   - Define typed `ToolRegistry` with schemas and parameter validators.
   - Unify manual controls and Maya under identical tool definitions (`image.*`, `project.*`).
   - Implement Maya natural language planner using Groq with structured outputs, fallback logic, project context resolution, and execution safety checks.
   - Interactive Maya panel in frontend with plan previews, execution logs, and direct output links.
5. **Quality Verification & Documentation:**
   - Comprehensive backend test suite covering all tools, models, storage, and planner mocks.
   - Frontend test suite covering Studio UI, controls, and Maya assistant.
   - Complete technical documentation across all architectural areas.

# MayaChitram — Extensible AI Creative Platform

MayaChitram is a production-minded creative platform built on the **"One Engine, Two Interaction Modes"** architecture. It pairs an interactive, dark-first **Image Studio** with **Maya**, a conversational AI creative assistant, backed by a deterministic image transformation engine, persistent projects, and non-destructive version history.

---

## 1. Key Capabilities

### 🎨 Stage 1 — Image Creator / Image Studio
- **Transform & Scale:** Resize with explicit dimensions, aspect-ratio preservation, and fit modes (`contain`, `cover`, `stretch`).
- **Aspect Presets:** 1:1 Square, 4:5 Instagram Portrait (1080×1350), 16:9 Landscape, 9:16 Story.
- **Crop:** Pixel-accurate crop bounds with boundary verification.
- **Orientation:** Clockwise rotation (90°, 180°, 270°) and horizontal/vertical flips.
- **Color & Light:** Interactive sliders for Brightness, Contrast, Saturation (including one-click Grayscale), and Color Temperature balancing (-100 Cool to +100 Warm).
- **Format Conversion & Compression:** Convert between WebP, JPEG, and PNG with quality compression settings (1–100%).
- **Alpha-Safe:** Automatic white background compositing when converting transparent PNGs to JPEG without crashes.
- **Before / After Comparison:** Hold or toggle to compare current edits directly against the original or parent version.
- **Export & Download:** One-click full-resolution export.

### 📁 Stage 2 — Unified Project & Asset Management
- **Persistent Projects:** Projects, assets, and operation history stored in SQLite (`WAL` mode, strict foreign keys).
- **Non-Destructive Versioning:** Every edit generates a new asset linked via `parent_asset_id`; original uploads are never overwritten.
- **Operation History:** Full audit trail tracking tool names, validated parameters, timestamps, and execution statuses.
- **Restart Resilient:** Full persistence surviving backend restarts.
- **Secure File Storage:** Random UUID-based storage keys with directory traversal protection.

### ✦ Stage 3 — Maya v1: AI Creative Assistant
- **Conversational Planning:** Translates natural-language requests into structured, validated tool plans via Groq (`llama-3.3-70b-versatile` or `llama-3.2-11b-vision-preview`).
- **Resilient Fallback:** Offline semantic parser supporting common creative requests even without Groq credentials.
- **Safety First:** Strict Pydantic parameter schemas; zero arbitrary shell or Python code execution.
- **One Engine, Two Modes:** Maya and the manual Studio UI execute through the exact same registered backend tools.

---

## 2. Architecture Overview

```text
┌───────────────────────────┐      ┌───────────────────────────┐
│    Manual Image Studio    │      │    Maya AI Assistant      │
└─────────────┬─────────────┘      └─────────────┬─────────────┘
              │                                  │
              └────────────────┬─────────────────┘
                               ▼
                      Shared Tool Registry
                               │
                       Validation Layer
                               │
                      Execution Service
                               │
                      Pillow Image Engine
                               │
                     SQLite & Local Storage
```

---

## 3. Technology Stack

- **Frontend:** React 18, TypeScript, Vite 6, Vitest, Testing Library, Vanilla CSS design system.
- **Backend:** Python 3.12+, FastAPI, Pillow (PIL), Pydantic Settings, SQLite3 with WAL mode.
- **AI Planning & Vision:** Groq Cloud API (`llama-3.3-70b-versatile` for tool planning, `llama-3.2-11b-vision-preview` for vision understanding).
- **Testing:** 22 backend automated tests (pytest), Vitest suite for frontend.
- **DevOps:** Docker Compose (`compose.yaml`).

---

## 4. Local Setup & Running

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm

### Backend
```bash
cd backend
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

Configure `backend/.env` (created from `backend/.env.example`):
```env
MAYACHITRAM_ENV=development
MAYACHITRAM_API_PREFIX=/api/v1
MAYACHITRAM_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
MAX_UPLOAD_BYTES=20971520
MAYACHITRAM_DATA_DIR=../data
GROQ_API_KEY=your_groq_api_key_here
GROQ_VISION_MODEL=llama-3.2-11b-vision-preview
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_SECONDS=45
```

Start Backend:
```bash
uvicorn mayachitram.main:app --reload --port 8000
```
- API Server: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### Frontend (in a separate terminal)
```bash
cd frontend
npm install
npm run dev
```
- Creative Studio UI: `http://localhost:5173`

### Run with Docker Compose
```bash
docker compose up --build
```

---

## 5. Verification & Tests

### Run Backend Tests & Linting
```bash
cd backend
python -m pytest
ruff check src tests
```

### Run Frontend Tests & Production Build
```bash
cd frontend
npm test
npm run build
```

### Structure Verification
```bash
python scripts/check-structure.py
```

---

## 6. Documentation Directory

- [`docs/IMPLEMENTATION_AUDIT.md`](docs/IMPLEMENTATION_AUDIT.md): Baseline codebase assessment and upgrade findings.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Detailed system design and component topology.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): Implemented stages and multi-engine future vision.
- [`docs/API.md`](docs/API.md): Complete REST endpoint contracts and schemas.
- [`docs/IMAGE_ENGINE.md`](docs/IMAGE_ENGINE.md): Pillow engine implementation and adding new tools.
- [`docs/MAYA_TOOL_SYSTEM.md`](docs/MAYA_TOOL_SYSTEM.md): AI tool registry, planning, and execution contracts.
- [`docs/STORAGE_AND_PROJECTS.md`](docs/STORAGE_AND_PROJECTS.md): SQLite persistence and storage security.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md): Local developer setup and commands.
- [`docs/TESTING.md`](docs/TESTING.md): Test suite organization and quality gates.
- [`docs/SECURITY.md`](docs/SECURITY.md): Threat model, decompression bomb guard, and key safety.

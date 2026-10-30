# MayaChitram System Architecture

## 1. Overview & Core Philosophy

MayaChitram is an extensible, AI-assisted creative platform designed around the **"One Engine, Two Interaction Modes"** architectural principle:

```text
Manual Image Studio Controls ────┐
                                 │
                                 ▼
                         Shared Tool Registry
                                 │
                          Validation Layer
                                 │
                         Execution Service
                                 │
                            Image Engine
                                 │
                    Asset & Operation Persistence
                                 ▲
                                 │
                          Execution Service
                                 ▲
                          Validation Layer
                                 ▲
                           Maya Planner
                                 ▲
                          Groq AI Provider
```

Every creative operation performed in MayaChitram—whether requested through manual slider/preset manipulation in the Image Studio UI, or requested via conversational natural language through Maya—routes through the **exact same tool registry**, validates against the **exact same Pydantic schema**, executes via the **exact same Pillow image engine**, and records into the **exact same non-destructive asset and operation history**.

---

## 2. Component Topology

```text
mayachitram/
├── frontend/                     # React 18 + Vite + TypeScript (Single-Page App)
│   ├── src/
│   │   ├── app/                  # Main shell and top-level workspace coordinators
│   │   ├── components/           # Reusable UI widgets (TopBar, etc.)
│   │   ├── features/
│   │   │   ├── image-studio/     # Image Studio (Canvas, ToolPanel, HistoryPanel)
│   │   │   ├── projects/         # Project selection and modal dialogs
│   │   │   ├── assets/           # Project Asset Filmstrip & upload dropzones
│   │   │   └── maya/             # Maya conversational planner & execution cards
│   │   ├── services/             # Typed API client functions
│   │   ├── styles/               # Design tokens, typography, dark creative theme
│   │   └── types/                # Domain interfaces (Asset, Project, Tool, Maya)
│   └── tests/                    # Testing Library / Vitest suites
│
├── backend/                      # Python 3.12+ Modular FastAPI Monolith
│   ├── src/mayachitram/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py     # Aggregated v1 API routing
│   │   │       ├── dependencies.py # FastAPI dependency injection
│   │   │       └── routes/       # Route handlers: image, projects, tools, maya, engines
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings with env prefix MAYACHITRAM_
│   │   │   └── errors.py         # Typed domain exceptions mapped to HTTP codes
│   │   ├── engines/
│   │   │   └── image/
│   │   │       ├── schemas.py    # Pydantic models for parameters and metadata
│   │   │       ├── service.py    # Pillow deterministic transformation engine
│   │   │       └── providers/    # Groq Vision adapter for image understanding
│   │   ├── storage/
│   │   │   └── service.py        # LocalStorageService with strict traversal security
│   │   ├── projects/
│   │   │   ├── models.py         # Project, Asset, Operation domain models
│   │   │   ├── repository.py     # SQLite persistence with foreign keys & migrations
│   │   │   └── service.py        # Project orchestration and asset ingestion
│   │   ├── maya/
│   │   │   ├── registry/         # ToolRegistry with registered image & project tools
│   │   │   ├── execution/        # Shared non-destructive execution coordinator
│   │   │   └── planner/          # Maya Groq planner + deterministic semantic fallback
│   │   └── main.py               # FastAPI entrypoint, CORS, global exception handler
│   └── tests/                    # 22+ automated pytest test cases
│
├── data/                         # Local database & binary media asset store (git-ignored)
└── compose.yaml                  # Containerized deployment orchestration
```

---

## 3. Storage & Persistence Architecture

- **Metadata Storage:** Embedded SQLite database located by default at `data/mayachitram.db` (configurable via `MAYACHITRAM_DATA_DIR`). Uses Write-Ahead Logging (`WAL`), strict foreign keys (`PRAGMA foreign_keys = ON;`), and migration tracking.
- **Binary Media Storage:** Binary files are stored in `data/storage/` under managed UUID-based relative paths (`projects/{project_id}/{uuid}.{ext}`).
- **Path Traversal Guard:** `LocalStorageService` strictly validates that all resolved paths are sub-paths of `root_dir`. User-supplied filenames are never used as disk paths.
- **Non-Destructive Lineage:** When a tool executes, the original asset remains untouched. A new asset record is created with `parent_asset_id` pointing to the input asset, allowing instant before/after comparisons and undo to any historical checkpoint.

---

## 4. Maya AI Planning Pipeline

1. **Context Aggregation:** Maya receives the target project ID, current active asset dimensions (width, height, format), list of available assets, and available tools.
2. **Groq Model Invocations:** If `GROQ_API_KEY` is provided, Maya requests a structured JSON plan from Groq (`llama-3.3-70b-versatile` or `llama-3.2-11b-vision-preview`).
3. **Deterministic Fallback Planner:** If Groq is unconfigured or unavailable, an internal semantic parser maps common creative prompts (such as "make square", "rotate 90 degrees", "resize to 1080x1350", "convert to webp", "brighten", "contrast", "warm") directly into verified tool parameters.
4. **Parameter Validation:** The proposed steps are validated against the `ToolRegistry` Pydantic schemas. Malformed parameters or unauthorized tools are blocked before execution.
5. **Execution Service:** Approved plans execute step-by-step through `ExecutionService`, chaining outputs from previous steps to subsequent steps.

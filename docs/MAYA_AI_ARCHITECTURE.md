# Maya AI — Unified Architecture & Integration Specification

**Version:** 1.0.0  
**Status:** Implemented & Verified  
**Core Principles:** One Engine, Two Modes • Grounded Quality Control • Non-Destructive Asset Lineage • Safe Extensibility  

---

## 1. Architectural Overview

Maya AI is the unified agentic creative assistant for the Mayachitram creative studio. Rather than functioning as an isolated text bot, Maya is embedded directly into the application's persistent project system, shared tool registry, and multi-step workflow orchestrator.

```
                          ┌───────────────────────────┐
                          │   Frontend React 18 UI    │
                          │   (Image Studio + Maya)   │
                          └─────────────┬─────────────┘
                                        │ HTTP / REST
                                        ▼
                          ┌───────────────────────────┐
                          │  FastAPI Router (v1/maya) │
                          └─────────────┬─────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
        ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
        │  Conversational │    │ Multi-Step DAG  │    │  Creative Recom- │
        │ Session Manager │    │   Orchestrator  │    │  mendations Svc  │
        └────────┬────────┘    └────────┬────────┘    └────────┬─────────┘
                 │                      │                      │
                 └──────────────────────┼──────────────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │    Shared Tool Registry   │
                          │   (Image, Design, Video)  │
                          └─────────────┬─────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
        ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
        │   Image Engine  │    │  Design Engine  │    │   Video Engine   │
        │     Adapter     │    │ Adapter (Draft) │    │  Adapter (Draft) │
        │  (10 Real PIL)  │    │  [Collaborator] │    │  [Collaborator]  │
        └────────┬────────┘    └─────────────────┘    └──────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │QualityValidator │
        │(Geometry/Format)│
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ LocalStorage &  │
        │ SQLite Database │
        └─────────────────┘
```

---

## 2. Key Modules & Implementation Map

| Module | Location | Purpose |
|---|---|---|
| **Maya Schemas** | `backend/src/mayachitram/maya/schemas.py` | Typed Pydantic models for workflows, DAG tasks, messages, recommendations, validation reports, and preferences. |
| **Maya Repository** | `backend/src/mayachitram/maya/repository.py` | SQLite WAL persistence for conversations, messages, workflows, tasks, and project brand memory. |
| **Tool Registry** | `backend/src/mayachitram/maya/registry/tools.py` | Typed discovery registry holding tool schemas, permission levels, timeout, and retry rules. |
| **Engine Adapters** | `backend/src/mayachitram/maya/registry/adapters.py` | Adapters for Image Engine (active), Design Engine (contract), and Video Engine (contract). |
| **Workflow Orchestrator** | `backend/src/mayachitram/maya/execution/workflow.py` | Topological DAG sort, dependency chaining, approval enforcement, retry handling, and error recovery. |
| **Creative Recommendations** | `backend/src/mayachitram/maya/planner/recommendations.py` | Context-aware suggestions for social formats (1:1, 4:5, 16:9), tone grades, and WebP compression. |
| **Quality Validation** | `backend/src/mayachitram/maya/validation/service.py` | Output verification (file presence, format conformity, dimension bounds, aspect ratio). |
| **Model Router** | `backend/src/mayachitram/maya/providers/router.py` | Primary Groq provider with automatic fallback to local semantic rule-based provider. |
| **API Endpoints** | `backend/src/mayachitram/api/v1/routes/maya.py` | REST API routes for chat, workflows, execution, cancellation, recommendations, and preferences. |
| **Maya UI Component** | `frontend/src/features/maya/MayaPanel.tsx` | Interactive React workspace supporting multi-turn chat, execution mode toggle, recommendations, and DAG viewer. |

---

## 3. Execution & Safety Modes

Maya supports 3 configurable execution modes:

1. **`ASSIST` (Recommendation Mode):**
   - Maya inspects context, suggests creative directions, and formulates draft workflow pipelines.
   - Maya never executes operations automatically; user must review and manually trigger execution.
2. **`EXECUTE` (Interactive Approval Mode - Default):**
   - Maya constructs executable DAG workflows.
   - Operations marked `requires_approval = True` (or destructive transforms) pause the pipeline with state `awaiting_approval` until the user confirms.
3. **`AUTONOMOUS` (Self-Directed Guarded Mode):**
   - Automatically executes verified workflows within strict safety boundaries (local project isolation, verified non-destructive storage keys).

---

## 4. API Endpoints

### Conversational Endpoints
- `POST /api/v1/maya/chat`
  - Body: `{"project_id": str, "message": str, "target_asset_id": str | null, "conversation_id": str | null, "execution_mode": "assist"|"execute"|"autonomous"}`
  - Returns: `SendMessageResponse` (user message, assistant message, active workflow if requested, contextual recommendations).
- `GET /api/v1/maya/conversations/{conversation_id}/messages`
  - Returns: `list[ConversationMessage]`.
- `GET /api/v1/maya/projects/{project_id}/conversations`
  - Returns: `list[ConversationSession]`.

### Durable DAG Workflow Endpoints
- `POST /api/v1/maya/workflows`
  - Body: `{"project_id": str, "user_prompt": str, "target_asset_id": str | null}`
  - Returns: `Workflow` with tasks, dependencies, and parameters.
- `GET /api/v1/maya/workflows/{workflow_id}`
  - Returns current `Workflow` state and individual task statuses.
- `POST /api/v1/maya/workflows/{workflow_id}/execute`
  - Body: `{"default_asset_id": str | null, "approved_task_ids": list[str]}`
  - Returns updated `Workflow`.
- `POST /api/v1/maya/workflows/{workflow_id}/cancel`
  - Transitions workflow to `cancelled`.

### Recommendations & Preferences
- `GET /api/v1/maya/projects/{project_id}/recommendations?asset_id={id}`
  - Returns `list[CreativeRecommendation]`.
- `POST /api/v1/maya/recommendations/apply`
  - Body: `{"project_id": str, "recommendation_id": str, "target_asset_id": str}`
  - Returns created `Workflow`.
- `GET /api/v1/maya/projects/{project_id}/preferences`
  - Returns `ProjectPreferences`.
- `PUT /api/v1/maya/projects/{project_id}/preferences`
  - Saves brand colors, preferred formats, and default execution mode.

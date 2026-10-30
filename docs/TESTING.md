# Testing & Quality Gates

MayaChitram enforces rigorous automated test coverage across frontend and backend layers.

---

## 1. Test Architecture

### Backend Tests (`backend/tests/`)
- `test_api.py`: Tests `/health`, platform engine discovery (`/api/v1/engines`), input content validation on empty and corrupted files.
- `test_image_engine.py`: Tests Pillow transformations:
  - Metadata inspection
  - Contain, cover, and stretch resize
  - Crop boundary assertion and negative coordinate rejection
  - 90°, 180°, 270° rotation and horizontal/vertical flips
  - Format conversions (WebP, JPEG, PNG)
  - RGBA PNG to JPEG transparency compositing over white canvas
  - Brightness, contrast, saturation, and color temperature shifts
  - Direct processing endpoint (`POST /api/v1/image/process`)
- `test_projects_and_storage.py`: Tests persistence and security:
  - LocalStorageService directory traversal protection
  - Project creation, retrieval, listing, updates, and deletion
  - Asset ingestion, metadata extraction, and binary download
  - Reopening SQLite database to simulate server restarts and verify persistence
  - Cascade deletion of assets from filesystem and database
- `test_maya_and_tools.py`: Tests tool contracts and conversational assistant:
  - Tool registry enumeration and schema availability
  - Non-destructive tool execution through `ExecutionService`
  - Parameter validation and invalid argument rejection
  - Maya fallback semantic planning for square crops and rotation
  - Maya Groq AI plan generation with mocked responses and sequential execution
  - REST endpoints for tools (`/tools`, `/tools/execute`) and Maya (`/maya/plan`, `/maya/execute`)

### Frontend Tests (`frontend/src/app/App.test.tsx`)
- App rendering with brand, header, and active project loading
- Topbar navigation and switching between Image Studio and Maya AI Assistant
- Tool panel tabs rendering (Transform, Crop, Color & Light, Export)
- Range sliders and preset buttons

---

## 2. Running the Test Suites

### Run Backend Tests
```bash
cd backend
python -m pytest
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

### Run Production Build Check
```bash
cd frontend
npm run build
```

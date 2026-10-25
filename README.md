# MayaChitram

MayaChitram is a modular multi-engine AI platform. V1.0 launches with an Image Engine for image description and visible-object identification.

## Architecture
```text
Browser -> frontend (React + TypeScript) -> backend (FastAPI)
                                             |
                                             +-- API v1
                                             +-- platform / engine registry
                                             +-- engines / image / service
                                                               |
                                                               +-- provider adapter
```

This is a monorepo with independently managed frontend and backend applications. The backend is a modular monolith, not a set of premature microservices.

## Stack
- Frontend: React, TypeScript, Vite, CSS
- Backend: Python 3.12+, FastAPI, Pydantic Settings
- Inference: hosted vision API behind a provider adapter
- Tests: Vitest + Testing Library; pytest + HTTPX
- Quality: Ruff, TypeScript strict mode
- Packaging: Docker Compose
- CI: GitHub Actions

## Local setup

Prerequisites: Python 3.12+, Node.js 20+, npm.

### Backend
```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cp .env.example .env  # Windows: copy .env.example .env
# Set GROQ_API_KEY in backend/.env for live inference
uvicorn mayachitram.main:app --reload --port 8000
```

### Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open the Vite URL (usually http://localhost:5173). API docs: http://localhost:8000/docs.

### Checks
```bash
cd backend && pytest && ruff check .
cd frontend && npm test && npm run build
```

### Docker
From the repository root, create `backend/.env` from `backend/.env.example`, then run:
```bash
docker compose up --build
```
Frontend: http://localhost:5173. API: http://localhost:8000.

## API
- `GET /health`
- `GET /api/v1/engines`
- `POST /api/v1/image/analyze` — multipart form field `file`

Accepted image formats: JPEG, PNG, WebP. Default max upload is 10 MiB.

## Scope and limitations
V1.0 provides scene descriptions and semantic object labels, not pixel-accurate bounding boxes. OCR, image embeddings/similarity search, accounts, persistence, and additional engines are planned, not implemented. Uploaded images are not persisted by this application, but provider retention policies must be reviewed. Do not expose publicly before implementing authentication, rate limiting, monitoring, and production security controls.

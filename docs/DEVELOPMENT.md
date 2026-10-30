# Development Guide

## 1. Prerequisites

- Python 3.12+
- Node.js 20+ & npm
- Git

---

## 2. Quickstart

### Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

Configure `backend/.env`:
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

Run Backend:
```bash
uvicorn mayachitram.main:app --reload --port 8000
```
API runs at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

---

## 3. Running Checks & Tests

### Backend Tests & Lint
```bash
cd backend
python -m pytest
ruff check src tests
ruff format --check src tests
```

### Frontend Tests & Build
```bash
cd frontend
npm test
npm run build
```

### Project Structure Check
```bash
python scripts/check-structure.py
```

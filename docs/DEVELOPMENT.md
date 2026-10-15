# VisionGuard AI — Local development

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for Postgres + full stack)

## Environment

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# SQLite default — no Docker required
$env:DATABASE_URL = "sqlite:///./visionguard.db"
python -m app.db.seed
uvicorn app.main:app --reload --app-dir .
```

API: http://127.0.0.1:8000/docs

Tests:

```powershell
cd backend
pytest
```

Format (optional): `ruff format .`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173  
Set `VITE_API_BASE_URL=http://127.0.0.1:8000` and `VITE_USE_MOCK=false` to hit the API.

```powershell
npm run build
npm run lint
npm test
```

## Docker Compose

From repo root:

```powershell
docker compose up --build
```

- Frontend: http://localhost:5173  
- Backend: http://localhost:8000  
- Postgres: localhost:5432 (`visionguard` / `visionguard` / `visionguard`)

## AI package

```powershell
cd ai
pip install -r requirements.txt
pytest
```

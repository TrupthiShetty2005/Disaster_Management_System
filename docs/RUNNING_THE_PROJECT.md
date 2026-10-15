# Running the project

Commands below match `frontend/package.json`, `backend/requirements.txt`, `scripts/seed_demo_data.py`, and `docker-compose.yml`.

## Prerequisites

- Python 3.11+ (developed with 3.13 in one environment)
- Node.js 20+ (`package.json` does not pin an engine)
- npm
- Optional: Docker Desktop (Compose file present; daemon must be running)

GPU is **not** required.

## Environment

From repo root:

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

Backend also reads `.env` from **cwd**. When you start uvicorn from `backend/`, copy or maintain `backend/.env` with the same keys as `.env.example`.

Important variables:

| Name | Role |
| --- | --- |
| `DATABASE_URL` | Default SQLite file |
| `CORS_ORIGINS` | Vite origins |
| `USE_MOCK_PROVIDERS` | Default true |
| `OPENWEATHER_API_KEY` | Optional; ignored if mock true |
| `YOLO_WEIGHTS_PATH` | Optional local file; never auto-download |
| `VITE_API_BASE_URL` | Frontend API host |
| `VITE_USE_MOCK` | `true` = UI mock data; `false` = call API |

Do not put real secrets in git.

## Database and seed

SQLite: created automatically on API startup.

```powershell
cd backend
..\venv\Scripts\python.exe ..\scripts\seed_demo_data.py
```

(or `python scripts/seed_demo_data.py` from repo root if `PYTHONPATH`/chdir in the script is used — the script `chdir`s to `backend/` itself.)

Seed no-ops if disasters already exist.

Postgres: set `DATABASE_URL` to the Compose URL. PostGIS image is for Docker; the app still uses JSON columns.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

This repo’s tests used `..\venv\Scripts\python.exe` from a root `venv/` in some setups; either venv is fine if packages from `requirements.txt` are installed.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite `server.port` is **5173**, `host: true`.

- UI: http://127.0.0.1:5173/dashboard

For API-backed demo: `VITE_USE_MOCK=false` and backend running.

## Docker

```powershell
docker compose up --build
```

Services: postgres 5432, backend 8000, frontend 5173. Compose sets mock providers / `VITE_USE_MOCK=true`. **Not verified** if Docker Desktop is stopped.

## Tests

```powershell
cd backend
$env:DATABASE_URL = "sqlite:///./test_visionguard.db"
pytest
```

```powershell
cd frontend
npm run lint
npm test
npm run build
```

`npm run build` runs `tsc --noEmit && vite build`.

AI stubs:

```powershell
cd ai
pip install -r requirements.txt
pytest
```

(`ai/requirements.txt` is pytest only.)

## Production build

Frontend: `npm run build` then `npm run preview`.  
Backend: no gunicorn script in repo; uvicorn is the documented server.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| UI has data but API is down | `VITE_USE_MOCK` is not `false` |
| CORS errors | `CORS_ORIGINS` includes the Vite origin |
| Empty DB | delete SQLite file or fix seed; `seed_if_empty` skips if any disaster exists |
| Vision 400 | file type/size/magic bytes in `vision/validation.py` |
| YOLO never runs | empty `YOLO_WEIGHTS_PATH` or missing ultralytics |
| Docker compose fails | Docker engine not running |
| Wrong app on :8000 | `src/main.py` is a **different** FastAPI; use `backend/app/main.py` |

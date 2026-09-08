# Disaster Management System

A simple Python web API built with FastAPI. It fetches weather and air quality data from OpenWeather.

See [Architecture Design](docs/ARCHITECTURE.md) for system overview, layers, request flows, and planned extensions.

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy the example env file and add your API key:

```powershell
copy .env.example .env
```

Get a free API key at [OpenWeather](https://openweathermap.org/api).

## Run

```powershell
python -m src.main
```

Or:

```powershell
uvicorn src.main:app --reload
```

Open http://127.0.0.1:8000/docs to try the API.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| GET | `/openweather/current?city=London` | Current weather |
| GET | `/openweather/forecast?city=London` | 5-day forecast |
| GET | `/openweather/air-quality?city=London` | Air quality |

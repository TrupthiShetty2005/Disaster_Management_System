from fastapi import FastAPI

from src.app.routes.noaa import router as noaa_router
from src.app.routes.openweather import router as openweather_router
from src.app.routes.nasa import router as nasa_router
app = FastAPI(
    title="Disaster Management System API",
    description="A simple API for weather and environmental data.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to Disaster Management System API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(openweather_router)
app.include_router(noaa_router)
app.include_router(nasa_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)

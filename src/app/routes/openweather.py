from fastapi import APIRouter
from src.app.services.openweather_services import fetch_current_weather,fetch_weather_forecast,fetch_air_quality
router = APIRouter(
    prefix="/openweather",
    tags=["OpenWeather"]
)

@router.get("/current")
def current_weather(city: str):
    return fetch_current_weather(city)

@router.get("/forecast")
def weather_forecast(city: str):
    return fetch_weather_forecast(city)

@router.get("/air-quality")
def air_quality(city: str):
    return fetch_air_quality(city)


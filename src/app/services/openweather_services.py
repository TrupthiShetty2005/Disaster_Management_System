import requests
from fastapi import HTTPException

from src.app.config.settings import OPENWEATHER_API_KEY

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def _require_api_key():
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENWEATHER_API_KEY is not set. Add it to your .env file.",
        )


def _get_json(url: str, params: dict):
    _require_api_key()
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if response.status_code != 200:
        message = data.get("message", "OpenWeather API request failed")
        raise HTTPException(status_code=response.status_code, detail=message)

    return data


def fetch_current_weather(city: str):
    data = _get_json(
        BASE_URL,
        {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
    )

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "weather": data["weather"][0]["description"],
    }


def fetch_weather_forecast(city: str):
    return _get_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
    )


def fetch_coordinates(city: str):
    locations = _get_json(
        "https://api.openweathermap.org/geo/1.0/direct",
        {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY},
    )

    if not locations:
        raise HTTPException(status_code=404, detail=f"City not found: {city}")

    return locations


def fetch_air_quality(city: str):
    location = fetch_coordinates(city)[0]

    return _get_json(
        "https://api.openweathermap.org/data/2.5/air_pollution",
        {
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": OPENWEATHER_API_KEY,
        },
    )

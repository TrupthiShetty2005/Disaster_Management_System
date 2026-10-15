from app.core.config import settings
from app.services.weather.live_provider import LiveWeatherProvider
from app.services.weather.mock_provider import MockWeatherProvider
from app.services.weather.models import WeatherProvider


def get_weather_provider() -> WeatherProvider:
    if settings.use_mock_providers:
        return MockWeatherProvider()
    return LiveWeatherProvider()

import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# OpenWeather Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# NOAA / NWS Configuration (User-Agent is required by api.weather.gov)
NOAA_USER_AGENT = os.getenv(
    "NOAA_USER_AGENT",
    "DisasterManagementSystem/1.0 (contact@example.com)",
)

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
from fastapi import APIRouter

from src.app.services.nasa_services import fetch_nasa_temperature


router = APIRouter(
    prefix="/nasa",
    tags=["NASA POWER"]
)


@router.get("/temperature-history")
def nasa_temperature_history(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
):
    return fetch_nasa_temperature(
        latitude,
        longitude,
        start_date,
        end_date
    )
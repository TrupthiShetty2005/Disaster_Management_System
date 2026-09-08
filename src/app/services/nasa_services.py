import requests


def fetch_nasa_temperature(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    params = {
        "parameters": "T2M",
        "community": "SB",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "JSON"
    }

    response = requests.get(url, params=params, timeout=30)

    response.raise_for_status()

    return response.json()
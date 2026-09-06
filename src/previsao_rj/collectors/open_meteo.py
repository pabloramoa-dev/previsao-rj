from __future__ import annotations
import requests

BASE = "https://api.open-meteo.com/v1/forecast"


def fetch_point(latitude: float, longitude: float, timezone: str = "America/Sao_Paulo") -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "forecast_days": 2,
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
            "precipitation_probability_max", "weather_code"
        ]),
        "hourly": ",".join([
            "temperature_2m", "apparent_temperature", "precipitation_probability",
            "precipitation", "weather_code", "wind_speed_10m", "wind_gusts_10m"
        ]),
    }
    r = requests.get(BASE, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

from __future__ import annotations
from datetime import datetime


def normalize_daily(location: dict, raw: dict) -> dict:
    d = raw["daily"]
    return {
        "id": location["id"],
        "name": location["name"],
        "min_c": round(float(d["temperature_2m_min"][0])),
        "max_c": round(float(d["temperature_2m_max"][0])),
        "rain_probability_pct": int(d.get("precipitation_probability_max", [0])[0] or 0),
        "rain_mm": float(d.get("precipitation_sum", [0])[0] or 0),
        "weather_code": int(d.get("weather_code", [0])[0] or 0),
    }


def build_snapshot(locations: list[dict], raws: list[dict]) -> dict:
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "open-meteo",
        "region": "rio_metropolitano",
        "forecast": {"today": {"locations": [normalize_daily(l, r) for l, r in zip(locations, raws)]}},
    }

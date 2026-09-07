"""Schema unico de snapshot — Plano Mestre v1.1, secoes 12.2 e 5.3.

Todo item publicado carrega `source`, `fetched_at`, `valid_for`, `model_run`,
`confidence` e `fallback_used`. O bloco `forecast.today.locations` mantem os
campos que o render e a legenda ja consomem, para nao quebrar o unico formato
que hoje funciona ponta a ponta.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .. import config
from ..collectors import open_meteo
from ..collectors.base import SourceResult, iso, now
from ..quality import confidence as conf

SCHEMA_VERSION = "2.0"

# Codigos WMO agrupados no vocabulario que o roteiro usa.
_CONDITION_BY_CODE = {
    0: "sol", 1: "sol entre nuvens", 2: "parcialmente nublado", 3: "nublado",
    45: "nevoeiro", 48: "nevoeiro", 51: "garoa", 53: "garoa", 55: "garoa",
    61: "chuva fraca", 63: "chuva", 65: "chuva forte",
    80: "pancadas", 81: "pancadas", 82: "pancadas fortes",
    95: "tempestade", 96: "tempestade com granizo", 99: "tempestade com granizo",
}


def condition_label(code: int | None) -> str:
    if code is None:
        return "indefinido"
    return _CONDITION_BY_CODE.get(int(code), "variavel")


def _daily_value(raw: dict[str, Any], field: str, index: int) -> Any:
    series = ((raw or {}).get("daily") or {}).get(field) or []
    return series[index] if index < len(series) else None


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _model_view(raw: dict[str, Any], day_index: int) -> dict[str, Any]:
    """Leitura de um modelo para um dia, no vocabulario interno."""
    max_c = _num(_daily_value(raw, "temperature_2m_max", day_index))
    min_c = _num(_daily_value(raw, "temperature_2m_min", day_index))
    prob = _num(_daily_value(raw, "precipitation_probability_max", day_index), 0.0)
    return {
        "max_c": max_c,
        "min_c": min_c,
        "apparent_max_c": _num(_daily_value(raw, "apparent_temperature_max", day_index)),
        "rain_probability_pct": prob,
        "rain_mm": _num(_daily_value(raw, "precipitation_sum", day_index), 0.0),
        "wind_gust_max_kmh": _num(_daily_value(raw, "wind_gusts_10m_max", day_index)),
        "uv_index_max": _num(_daily_value(raw, "uv_index_max", day_index)),
        "weather_code": _daily_value(raw, "weather_code", day_index),
    }


def rain_window(raw: dict[str, Any], day: str,
                threshold_pct: float = 45.0) -> dict[str, Any] | None:
    """Janela horaria em que a chuva concentra o risco no dia pedido.

    O plano (secao 8.1 e 10.1) exige penalizar chuva NA JANELA DE USO, nao o
    total diario — por isso a janela viaja junto com o dado.
    """
    hourly = (raw or {}).get("hourly") or {}
    times = hourly.get("time") or []
    probs = hourly.get("precipitation_probability") or []
    if not times or not probs:
        return None
    hits = [(t, _num(p, 0.0) or 0.0) for t, p in zip(times, probs)
            if t.startswith(day) and (_num(p, 0.0) or 0.0) >= threshold_pct]
    if not hits:
        return None
    peak_time, peak = max(hits, key=lambda item: item[1])
    return {
        "start": hits[0][0][11:16],
        "end": hits[-1][0][11:16],
        "peak_hour": peak_time[11:16],
        "peak_probability_pct": round(peak),
        "threshold_pct": threshold_pct,
    }


def _location_entry(loc: dict[str, Any],
                    per_model_raw: dict[str, dict[str, Any]],
                    primary_model: str,
                    day_index: int,
                    day: str) -> dict[str, Any]:
    views = {model: _model_view(raw, day_index) for model, raw in per_model_raw.items()}
    reference = views.get(primary_model) or next(iter(views.values()))

    maxima = [v["max_c"] for v in views.values() if v["max_c"] is not None]
    probs = [v["rain_probability_pct"] for v in views.values()
             if v["rain_probability_pct"] is not None]

    entry: dict[str, Any] = {
        # --- campos consumidos pelo render e pela legenda (nao renomear) ---
        "id": loc["id"],
        "name": loc["name"],
        "min_c": round(reference["min_c"]) if reference["min_c"] is not None else None,
        "max_c": round(reference["max_c"]) if reference["max_c"] is not None else None,
        "rain_probability_pct": int(round(reference["rain_probability_pct"] or 0)),
        "rain_mm": round(reference["rain_mm"] or 0.0, 1),
        "weather_code": int(reference["weather_code"] or 0),
        # --- contexto editorial ---
        "condition": condition_label(reference["weather_code"]),
        "zone": loc["zone"],
        "municipality": loc["municipality"],
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "spatial_fit": loc["spatial_fit"],
        "sample_tier": loc["sample_tier"],
        "beach": bool(loc.get("beach", False)),
        "apparent_max_c": (round(reference["apparent_max_c"])
                           if reference["apparent_max_c"] is not None else None),
        "wind_gust_max_kmh": (round(reference["wind_gust_max_kmh"])
                              if reference["wind_gust_max_kmh"] is not None else None),
        "uv_index_max": (round(reference["uv_index_max"], 1)
                         if reference["uv_index_max"] is not None else None),
        "rain_window": rain_window(per_model_raw.get(primary_model, {}), day),
        # --- procedencia e dispersao ---
        "models": views,
        "primary_model": primary_model,
        "agreement": {
            "models_used": len(views),
            "max_c_spread": round(max(maxima) - min(maxima), 1) if len(maxima) > 1 else 0.0,
            "rain_probability_spread_pct": (round(max(probs) - min(probs))
                                            if len(probs) > 1 else 0),
        },
    }
    return entry


def _day_block(locations: list[dict[str, Any]],
               per_model_points: dict[str, dict[str, dict[str, Any]]],
               primary_model: str,
               day_index: int,
               day: str) -> dict[str, Any]:
    entries = []
    for loc in locations:
        per_model_raw = {model: points.get(loc["id"], {})
                         for model, points in per_model_points.items()}
        per_model_raw = {m: raw for m, raw in per_model_raw.items() if raw}
        if not per_model_raw:
            continue
        entries.append(_location_entry(loc, per_model_raw, primary_model, day_index, day))
    return {"date": day, "locations": entries}


def build(
    collected: dict[str, SourceResult],
    locations: list[dict[str, Any]],
    *,
    previous_snapshot: dict[str, Any] | None = None,
    observed: SourceResult | None = None,
    marine: SourceResult | None = None,
    beach_status: SourceResult | None = None,
) -> dict[str, Any]:
    """Monta o snapshot completo a partir do que os coletores devolveram."""
    effective = open_meteo.effective_primary(collected)
    if effective is None:
        detail = "; ".join(f"{m}: {r.status} {r.detail or ''}".strip()
                           for m, r in collected.items())
        raise RuntimeError(f"nenhum modelo meteorologico utilizavel ({detail})")
    primary_model, primary_result = effective

    per_model_points = {model: (result.payload or {}).get("points", {})
                        for model, result in collected.items() if result.usable}

    # O dia de referencia vem do proprio dado servido, nao do relogio da maquina:
    # assim uma fixture e um render sempre falam do mesmo dia (secao 14.2).
    reference_days = _reference_days(per_model_points.get(primary_model, {}))
    days = {"today": reference_days[0], "tomorrow": reference_days[1]}
    forecast = {
        key: _day_block(locations, per_model_points, primary_model, index, day)
        for index, (key, day) in enumerate(days.items())
    }

    spec = config.source(open_meteo.SOURCE)
    reference_entries = forecast["today"]["locations"]
    hottest = max(reference_entries, key=lambda e: e["max_c"] or -99, default=None)

    previous_reference = None
    if previous_snapshot and hottest:
        for entry in (previous_snapshot.get("forecast", {})
                      .get("today", {}).get("locations", [])):
            if entry.get("id") == hottest["id"]:
                previous_reference = entry
                break

    per_model_reference = ({m: v for m, v in hottest["models"].items()} if hottest else {})

    observed_status = observed.status if observed else "not_collected"
    confidence = conf.compute(
        per_model=per_model_reference,
        age_minutes=primary_result.age_minutes,
        freshness_ttl_minutes=float(spec.get("freshness_ttl_minutes", 120)),
        previous_reference=previous_reference,
        current_reference=hottest or {},
        observed_status=observed_status,
        observation_agreement=None,
        spatial_fits=[e["spatial_fit"] for e in reference_entries],
    )

    sources = [result.to_dict() for result in collected.values()]
    for extra in (observed, marine, beach_status):
        if extra is not None:
            sources.append(extra.to_dict())

    fallback_used = any(s.get("fallback_used") for s in sources)

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(),
        "timezone": "America/Sao_Paulo",
        "region": "rio_metropolitano",
        "coverage": sorted({loc["municipality"] for loc in locations}),
        "forecast": {
            **forecast,
            # confianca tambem no bloco do dia: e la que o render e o motor olham
            "today_confidence": confidence["score"],
            "models": sorted(per_model_points),
            "primary_model": primary_model,
        },
        "observed": _extra_block(observed),
        "marine": _extra_block(marine),
        "beach_status": _extra_block(beach_status),
        "events": [],
        "football": [],
        "mobility": [],
        "confidence": confidence,
        "sources": sources,
        "fallback_used": fallback_used,
        "valid_for": primary_result.valid_for,
        "model_run": primary_result.model_run,
    }
    # Compatibilidade com o codigo que le forecast.today.confidence.
    snapshot["forecast"]["today"]["confidence"] = confidence["score"]
    snapshot["forecast"]["tomorrow"]["confidence"] = confidence["score"]
    return snapshot


def _reference_days(points: dict[str, dict[str, Any]]) -> list[str]:
    """Datas servidas pelo modelo principal; cai no relogio local se faltar."""
    for raw in points.values():
        times = ((raw or {}).get("daily") or {}).get("time") or []
        if len(times) >= 2:
            return [times[0], times[1]]
    today = date.today()
    return [today.isoformat(), (today + timedelta(days=1)).isoformat()]


def _extra_block(result: SourceResult | None) -> dict[str, Any]:
    if result is None:
        return {"status": "not_collected"}
    block = result.to_dict()
    if result.usable and isinstance(result.payload, dict):
        block["data"] = result.payload
    return block


def is_stale(snapshot: dict[str, Any], ttl_minutes: float | None = None,
             reference: datetime | None = None) -> bool:
    """Gate de frescor do snapshot (secoes 8.1 e 13.4)."""
    if ttl_minutes is None:
        ttl_minutes = float(config.load_thresholds().get("snapshot_ttl_minutes", 120))
    generated = datetime.fromisoformat(snapshot["generated_at"])
    age = ((reference or now()) - generated).total_seconds() / 60
    return age > ttl_minutes


# ---------------------------------------------------------------------------
# Compatibilidade com o piloto v1 (mantida para nao quebrar codigo existente).
# ---------------------------------------------------------------------------

def normalize_daily(location: dict, raw: dict) -> dict:
    view = _model_view(raw, 0)
    return {
        "id": location["id"],
        "name": location["name"],
        "min_c": round(view["min_c"]) if view["min_c"] is not None else None,
        "max_c": round(view["max_c"]) if view["max_c"] is not None else None,
        "rain_probability_pct": int(round(view["rain_probability_pct"] or 0)),
        "rain_mm": round(view["rain_mm"] or 0.0, 1),
        "weather_code": int(view["weather_code"] or 0),
    }


def build_snapshot(locations: list[dict], raws: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": iso(),
        "source": "open-meteo",
        "region": "rio_metropolitano",
        "forecast": {"today": {"locations": [normalize_daily(l, r)
                                             for l, r in zip(locations, raws)]}},
    }

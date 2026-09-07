"""Coletor meteorologico multi-modelo e multi-ponto.

Plano Mestre secoes 5.1 e 12.1: ECMWF IFS como modelo principal, modelos
secundarios do proprio Open-Meteo apenas para COMPARACAO (a concordancia entre
eles vira o criterio de maior peso do score de confianca, secao 5.2).

Uma requisicao por modelo, com todas as coordenadas de uma vez: o Open-Meteo
devolve uma lista na mesma ordem em que os pontos foram enviados.
"""
from __future__ import annotations

from typing import Any, Iterable

import requests

from .. import config
from .base import SourceResult, get_json, iso, not_collected

SOURCE = "open_meteo_forecast"

DAILY_FIELDS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_gusts_10m_max",
    "uv_index_max",
    "weather_code",
]

HOURLY_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
]


def _params(locations: list[dict[str, Any]], model: str, timezone_name: str) -> dict[str, Any]:
    return {
        "latitude": ",".join(f"{l['latitude']:.4f}" for l in locations),
        "longitude": ",".join(f"{l['longitude']:.4f}" for l in locations),
        "timezone": timezone_name,
        "forecast_days": 3,
        "models": model,
        "daily": ",".join(DAILY_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
    }


def _as_list(payload: Any) -> list[dict[str, Any]]:
    """O Open-Meteo devolve objeto para 1 ponto e lista para varios."""
    if isinstance(payload, list):
        return payload
    return [payload]


def fetch_model(
    locations: list[dict[str, Any]],
    model: str,
    *,
    timezone_name: str = "America/Sao_Paulo",
    session: requests.Session | None = None,
) -> SourceResult:
    """Coleta um modelo para todos os pontos. Nao levanta excecao de rede."""
    if not locations:
        return not_collected(SOURCE, "nenhum local na amostra")
    spec = config.source(SOURCE)
    result = get_json(
        SOURCE,
        spec["endpoint"],
        _params(locations, model, timezone_name),
        cache_key=f"{model}|" + ",".join(l["id"] for l in locations),
        session=session,
    )
    if result.usable or result.status == "degraded":
        entries = _as_list(result.payload)
        if len(entries) != len(locations):
            return SourceResult(SOURCE, "failed",
                                detail=f"{model}: esperados {len(locations)} pontos, "
                                       f"vieram {len(entries)}")
        result.payload = {"model": model,
                          "points": {loc["id"]: raw for loc, raw in zip(locations, entries)}}
        result.model_run = _model_run(entries[0], model)
        result.valid_for = _valid_for(entries[0])
    # Cada modelo entra no bloco `sources` com nome proprio: tres linhas
    # "open_meteo_forecast" identicas nao dizem qual modelo falhou.
    result.name = f"{SOURCE}:{model}"
    return result


def fetch_all_models(
    locations: list[dict[str, Any]],
    *,
    timezone_name: str = "America/Sao_Paulo",
    session: requests.Session | None = None,
) -> dict[str, SourceResult]:
    """Modelo principal + secundarios. O principal define os numeros publicados;
    os secundarios so entram no calculo de concordancia."""
    spec = config.source(SOURCE)
    models = spec.get("models") or {}
    primary = models.get("primary", "ecmwf_ifs025")
    secondary: Iterable[str] = models.get("secondary") or []

    collected = {primary: fetch_model(locations, primary,
                                      timezone_name=timezone_name, session=session)}
    for model in secondary:
        collected[model] = fetch_model(locations, model,
                                       timezone_name=timezone_name, session=session)

    # Fallback declarado em fontes.yaml: sem o ECMWF, promove o primeiro
    # secundario utilizavel e marca fallback_used no snapshot.
    if not collected[primary].usable and spec.get("fallback") == "secondary_model":
        for model in secondary:
            if collected[model].usable:
                collected[model].fallback_used = True
                collected[model].detail = (
                    f"promovido a principal: {primary} indisponivel "
                    f"({collected[primary].detail or collected[primary].status})"
                )
                break
    return collected


def primary_model_name() -> str:
    return (config.source(SOURCE).get("models") or {}).get("primary", "ecmwf_ifs025")


def effective_primary(collected: dict[str, SourceResult]) -> tuple[str, SourceResult] | None:
    """Modelo que de fato fornece os numeros publicados, considerando fallback."""
    primary = primary_model_name()
    if primary in collected and collected[primary].usable:
        return primary, collected[primary]
    for model, result in collected.items():
        if result.usable:
            return model, result
    return None


def _valid_for(raw: dict[str, Any]) -> str | None:
    daily = (raw or {}).get("daily") or {}
    times = daily.get("time") or []
    return f"{times[0]}..{times[-1]}" if times else None


def _model_run(raw: dict[str, Any], model: str) -> str | None:
    """Marcador da rodada.

    O endpoint de previsao do Open-Meteo nao devolve o horario da rodada. Em vez
    de inventar um valor, registramos o inicio da serie horaria servida, que e o
    que temos de verificavel. A atualidade real e medida por `fetched_at` e pela
    idade do cache no score de confianca (secao 5.2).
    """
    hourly = (raw or {}).get("hourly") or {}
    times = hourly.get("time") or []
    return f"{model}@serie_inicia_{times[0]}" if times else None


def daily_index_for(raw: dict[str, Any], day_offset: int) -> int | None:
    times = ((raw or {}).get("daily") or {}).get("time") or []
    return day_offset if 0 <= day_offset < len(times) else None


def fetch_point(latitude: float, longitude: float,
                timezone: str = "America/Sao_Paulo") -> dict:
    """Compatibilidade com o piloto anterior (scripts/collect_live.py antigo)."""
    spec = config.source(SOURCE)
    response = requests.get(spec["endpoint"], params={
        "latitude": latitude, "longitude": longitude, "timezone": timezone,
        "forecast_days": 2,
        "daily": ",".join(DAILY_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
    }, timeout=int(spec.get("timeout_seconds", 25)))
    response.raise_for_status()
    return response.json()

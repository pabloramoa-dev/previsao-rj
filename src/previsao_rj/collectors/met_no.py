"""Provedor independente: MET Norway (locationforecast 2.0 compact).

Por que existe (Plano Mestre secao 5.2): o criterio de maior peso do score de
confianca e a concordancia entre modelos, mas ate aqui icon, ecmwf e gfs vinham
todos pelo Open-Meteo. Tres modelos da mesma casa, pelo mesmo pipeline, no mesmo
endpoint: se o Open-Meteo cai ou devolve 429, os tres somem juntos e a
"concordancia" nunca foi entre PROVEDORES. A met.no e a segunda opiniao de
verdade — outro instituto, outro processamento, outra infraestrutura.

E o segundo papel e ser rede de protecao: se nenhum modelo do Open-Meteo estiver
utilizavel, `effective_primary` promove a met.no e o snapshot sai mesmo assim,
marcado como fallback.

Escolha deliberada do endpoint `compact`: e o mesmo que ja roda em producao ha
meses no pipeline irmao, com comportamento conhecido. O `complete` traria
temperatura aparente e indice UV, mas nao traz rajada nem probabilidade de chuva
nesta latitude — os campos que faltam faltam nos dois.

O QUE A MET.NO NAO DA PARA O RIO, e que por isso fica ausente em vez de virar
zero: rajada de vento, probabilidade de chuva e indice UV. Esses campos so
existem no modelo de alta resolucao nordico. O normalizador ja sabe lidar com
campo ausente (escolhe o primeiro modelo que tenha o valor), e o
`model_agreement` ja ignora modelo sem o campo — entao a met.no contribui para a
concordancia de TEMPERATURA e fica fora da de chuva, sem inventar numero.

Requisito da met.no: toda requisicao precisa de User-Agent identificando o
projeto, senao a resposta e 403. Ele e declarado em `fontes.yaml`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .. import config
from .base import SourceResult, get_json, iso, not_collected

SOURCE = "met_no_forecast"
MODEL = "met_no"

TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo, sem DST desde 2019

# symbol_code da met.no -> codigo WMO, o vocabulario que `condition_label` usa.
# A chave e o simbolo sem o sufixo _day/_night/_polartwilight.
_SYMBOL_TO_WMO = {
    "clearsky": 0,
    "fair": 1,
    "partlycloudy": 2,
    "cloudy": 3,
    "fog": 45,
    "lightrainshowers": 80,
    "rainshowers": 81,
    "heavyrainshowers": 82,
    "lightrain": 61,
    "rain": 63,
    "heavyrain": 65,
    "lightsleet": 61,
    "sleet": 63,
    "heavysleet": 65,
    "lightsnow": 71,
    "snow": 73,
    "heavysnow": 75,
    "lightsleetshowers": 80,
    "sleetshowers": 81,
    "heavysleetshowers": 82,
    "lightsnowshowers": 85,
    "snowshowers": 86,
    "heavysnowshowers": 86,
}
_THUNDER_WMO = 95


def symbol_to_weather_code(symbol: str | None) -> int | None:
    """Converte o simbolo da met.no no codigo WMO equivalente.

    Trovoada vence: 'rainandthunder' e chuva, mas o que muda a decisao editorial
    e o raio. Simbolo desconhecido devolve None em vez de um codigo chutado.
    """
    if not isinstance(symbol, str) or not symbol:
        return None
    base = symbol.split("_")[0]
    if "thunder" in base:
        return _THUNDER_WMO
    return _SYMBOL_TO_WMO.get(base)


def _local(instant: str) -> str:
    """ISO em UTC -> horario local sem fuso, no mesmo formato do Open-Meteo.

    O alinhamento horario entre provedores e feito por string ('2026-09-12T15:00'),
    entao os dois lados precisam falar o mesmo idioma de tempo.
    """
    moment = datetime.fromisoformat(instant.replace("Z", "+00:00")).astimezone(TZ)
    return moment.strftime("%Y-%m-%dT%H:%M")


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_open_meteo_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Traduz a resposta da met.no para o formato que o normalizador ja consome.

    Campos que a met.no nao fornece sao OMITIDOS, nao zerados: chave ausente faz
    o normalizador cair no proximo modelo, enquanto um zero mentiria.
    """
    series = ((payload or {}).get("properties") or {}).get("timeseries") or []

    hourly: dict[str, list[Any]] = {
        "time": [], "temperature_2m": [], "precipitation": [],
        "weather_code": [], "cloud_cover": [], "wind_speed_10m": [],
    }
    por_dia: dict[str, dict[str, Any]] = {}

    for point in series:
        instant = point.get("time")
        if not isinstance(instant, str):
            continue
        local = _local(instant)
        day = local[:10]
        details = ((point.get("data") or {}).get("instant") or {}).get("details") or {}
        next_hour = (point.get("data") or {}).get("next_1_hours") or {}

        temperature = _num(details.get("air_temperature"))
        cloud = _num(details.get("cloud_area_fraction"))
        wind_ms = _num(details.get("wind_speed"))
        rain = _num((next_hour.get("details") or {}).get("precipitation_amount"))
        code = symbol_to_weather_code((next_hour.get("summary") or {}).get("symbol_code"))

        hourly["time"].append(local)
        hourly["temperature_2m"].append(temperature)
        hourly["precipitation"].append(rain)
        hourly["weather_code"].append(code)
        hourly["cloud_cover"].append(cloud)
        hourly["wind_speed_10m"].append(round(wind_ms * 3.6, 1) if wind_ms is not None else None)

        bucket = por_dia.setdefault(day, {"temps": [], "rain": 0.0, "tem_chuva": False,
                                          "codes": []})
        if temperature is not None:
            bucket["temps"].append(temperature)
        if rain is not None:
            bucket["rain"] += rain
            bucket["tem_chuva"] = True
        if code is not None:
            bucket["codes"].append(code)

    daily: dict[str, list[Any]] = {
        "time": [], "temperature_2m_max": [], "temperature_2m_min": [],
        "precipitation_sum": [], "weather_code": [],
    }
    for day in sorted(por_dia):
        bucket = por_dia[day]
        temps = bucket["temps"]
        daily["time"].append(day)
        daily["temperature_2m_max"].append(round(max(temps), 1) if temps else None)
        daily["temperature_2m_min"].append(round(min(temps), 1) if temps else None)
        daily["precipitation_sum"].append(round(bucket["rain"], 1) if bucket["tem_chuva"] else None)
        # Dia inteiro resumido pelo tempo mais severo: e o que decide a pauta.
        daily["weather_code"].append(max(bucket["codes"]) if bucket["codes"] else None)

    return {"daily": daily, "hourly": hourly}


def fetch(
    locations: list[dict[str, Any]],
    *,
    session: requests.Session | None = None,
) -> SourceResult:
    """Uma requisicao por ponto (a met.no nao aceita multiponto).

    Falha de um ponto nao derruba a coleta: o ponto fica de fora e o detalhe
    registra quais faltaram. So devolve 'failed' se nenhum ponto responder.
    """
    if not locations:
        return not_collected(SOURCE, "nenhum local na amostra")
    spec = config.source(SOURCE)
    if not spec.get("enabled", False):
        return not_collected(SOURCE)

    points: dict[str, dict[str, Any]] = {}
    faltaram: list[str] = []
    idades: list[float] = []
    algum_cache = False

    for loc in locations:
        params = {"lat": f"{loc['latitude']:.4f}", "lon": f"{loc['longitude']:.4f}"}
        result = get_json(SOURCE, spec["endpoint"], params,
                          cache_key=f"{loc['id']}:{params['lat']},{params['lon']}",
                          session=session)
        if not result.ok or not result.payload:
            faltaram.append(loc["id"])
            continue
        points[loc["id"]] = to_open_meteo_shape(result.payload)
        idades.append(result.age_minutes)
        algum_cache = algum_cache or result.status in {"cached", "degraded"}

    if not points:
        return SourceResult(f"{SOURCE}:{MODEL}", "failed",
                            detail=f"nenhum ponto respondeu ({len(faltaram)} tentados)")

    primeiro = next(iter(points.values()))
    dias = primeiro["daily"]["time"]
    horas = primeiro["hourly"]["time"]
    return SourceResult(
        name=f"{SOURCE}:{MODEL}",
        status="cached" if algum_cache else "ok",
        payload={"model": MODEL, "points": points},
        model_run=f"{MODEL}@serie_inicia_{horas[0]}" if horas else None,
        valid_for=f"{dias[0]}..{dias[-1]}" if dias else None,
        age_minutes=round(max(idades), 1) if idades else 0.0,
        detail=(f"pontos sem resposta: {', '.join(faltaram)}" if faltaram else None),
    )


def collect(locations: list[dict[str, Any]],
            *, session: requests.Session | None = None) -> dict[str, SourceResult]:
    """Formato pronto para entrar no dicionario de modelos do snapshot."""
    return {MODEL: fetch(locations, session=session)}

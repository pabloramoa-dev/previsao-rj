# -*- coding: utf-8 -*-
"""Coleta de previsao para o atendimento em tempo real.

Uma unica rodada de requisicoes ao Open-Meteo traz hoje e amanha de TODOS os
pontos do cadastro (config/locais_rj.yaml), em lotes de 25 coordenadas. O
resultado fica em memoria por TTL_SEGUNDOS, entao o robo bate na API poucas
vezes por hora e nao uma vez por seguidor.

Se a API falhar e houver cache recente, o cache e servido: previsao de duas
horas atras ainda ajuda quem perguntou; silencio nao ajuda em nada. Se nao
houver cache nenhum, o MET Norway responde pelo ponto pedido — uma requisicao
so, sob demanda, porque o fallback nao precisa aquecer a cidade inteira.

Praias nao entram como ponto proprio: o resolver ja aponta praia para o bairro
(Ipanema -> ipanema), e o modelo de referencia trabalha em grade de ~9 km, onde
a areia e a quadra vizinha caem na mesma celula.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import threading
import time

import requests

from .. import config

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MET_NO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
MET_NO_UA = "previsaorj-atendimento/1.0 github.com/pabloramoa-dev/previsao-rj"
TIMEZONE = "America/Sao_Paulo"
TIMEOUT = 20
LOTE = 25

TTL_SEGUNDOS = 20 * 60
TTL_EMERGENCIA = 3 * 60 * 60
COOLDOWN_429 = 60

DIARIO = ("temperature_2m_min,temperature_2m_max,"
          "precipitation_probability_max,wind_gusts_10m_max,uv_index_max")

_cache: dict[str, dict] | None = None
_cache_em: float = 0.0
_bloqueado_ate: float = 0.0
_trava = threading.Lock()


def pontos() -> dict[str, dict]:
    """{id: local} de tudo que pode virar resposta: bairros e POIs com coordenada.

    Praias ficam de fora porque o resolver as devolve como bairro.
    """
    lugares = config.load_places()
    saida = {l["id"]: l for l in lugares["locations"]}
    for grupo, itens in (lugares.get("points_of_interest") or {}).items():
        if grupo == "beaches":
            continue
        for poi in itens:
            saida.setdefault(poi["id"], poi)
    return saida


def _numero(valor, padrao: float = 0.0) -> float:
    """Open-Meteo devolve null em campo sem dado; isso nao pode virar erro."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _serie(bloco: dict, chave: str, indice: int) -> float:
    dados = (bloco.get("daily") or {}).get(chave) or []
    return _numero(dados[indice] if indice < len(dados) else None)


def _do_bloco(bloco: dict, fonte: str) -> dict:
    return {
        "tmin": _serie(bloco, "temperature_2m_min", 0),
        "tmax": _serie(bloco, "temperature_2m_max", 0),
        "prob_chuva": _serie(bloco, "precipitation_probability_max", 0),
        "rajada_kmh": _serie(bloco, "wind_gusts_10m_max", 0),
        "uv": _serie(bloco, "uv_index_max", 0),
        "tmin_amanha": _serie(bloco, "temperature_2m_min", 1),
        "tmax_amanha": _serie(bloco, "temperature_2m_max", 1),
        "prob_chuva_amanha": _serie(bloco, "precipitation_probability_max", 1),
        "rajada_kmh_amanha": _serie(bloco, "wind_gusts_10m_max", 1),
        "uv_amanha": _serie(bloco, "uv_index_max", 1),
        "_fonte": fonte,
    }


def _coletar() -> dict[str, dict]:
    locais = list(pontos().values())
    saida: dict[str, dict] = {}
    for inicio in range(0, len(locais), LOTE):
        lote = locais[inicio:inicio + LOTE]
        resposta = requests.get(
            FORECAST_URL,
            params={
                "latitude": ",".join(str(l["latitude"]) for l in lote),
                "longitude": ",".join(str(l["longitude"]) for l in lote),
                "daily": DIARIO,
                "timezone": TIMEZONE,
                "forecast_days": 2,
            },
            timeout=TIMEOUT,
        )
        resposta.raise_for_status()
        bruto = resposta.json()
        # Com varias coordenadas a API devolve lista; com uma so, um objeto.
        blocos = bruto if isinstance(bruto, list) else [bruto]
        if len(blocos) != len(lote):
            raise RuntimeError(
                f"pedi {len(lote)} pontos e o Open-Meteo devolveu {len(blocos)}")
        for local, bloco in zip(lote, blocos):
            saida[local["id"]] = _do_bloco(bloco, "open_meteo")
    return saida


def _met_no(local: dict) -> dict:
    """Fallback gratuito do MET Norway para um ponto so."""
    fuso = ZoneInfo(TIMEZONE)
    hoje = datetime.now(fuso).date()
    datas = [hoje, hoje + timedelta(days=1)]

    resposta = requests.get(
        MET_NO_URL,
        params={"lat": f"{local['latitude']:.4f}",
                "lon": f"{local['longitude']:.4f}"},
        headers={"User-Agent": MET_NO_UA},
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    series = resposta.json().get("properties", {}).get("timeseries", [])

    balde = {d: {"temp": [], "chuva": [], "vento": []} for d in datas}
    for ponto in series:
        instante = datetime.fromisoformat(
            ponto["time"].replace("Z", "+00:00")).astimezone(fuso)
        if instante.date() not in balde:
            continue
        bloco = ponto.get("data", {})
        detalhes = bloco.get("instant", {}).get("details", {})
        atual = balde[instante.date()]
        if detalhes.get("air_temperature") is not None:
            atual["temp"].append(_numero(detalhes["air_temperature"]))
        vento = detalhes.get("wind_speed_of_gust", detalhes.get("wind_speed"))
        if vento is not None:
            atual["vento"].append(_numero(vento) * 3.6)
        periodo = (bloco.get("next_1_hours") or bloco.get("next_6_hours") or {})
        det = periodo.get("details", {})
        prob = det.get("probability_of_precipitation")
        if prob is None and det.get("precipitation_amount") is not None:
            prob = 100.0 if _numero(det["precipitation_amount"]) > 0.1 else 0.0
        if prob is not None:
            atual["chuva"].append(_numero(prob))

    if not balde[datas[0]]["temp"]:
        raise RuntimeError(f"MET Norway sem dados para {local['id']}")

    def resumo(dia):
        b = balde[dia]
        if not b["temp"]:
            b = balde[datas[0]]
        return (min(b["temp"]), max(b["temp"]),
                max(b["chuva"] or [0.0]), max(b["vento"] or [0.0]))

    h, a = resumo(datas[0]), resumo(datas[1])
    return {
        "tmin": h[0], "tmax": h[1], "prob_chuva": h[2], "rajada_kmh": h[3],
        "uv": 0.0,
        "tmin_amanha": a[0], "tmax_amanha": a[1],
        "prob_chuva_amanha": a[2], "rajada_kmh_amanha": a[3],
        "uv_amanha": 0.0,
        "_fonte": "met_no",
    }


def previsao() -> dict[str, dict]:
    """Hoje e amanha de todos os pontos do cadastro, com cache."""
    global _cache, _cache_em, _bloqueado_ate
    agora = time.time()
    if _cache is not None and agora - _cache_em < TTL_SEGUNDOS:
        return _cache

    with _trava:
        agora = time.time()
        if _cache is not None and agora - _cache_em < TTL_SEGUNDOS:
            return _cache
        if agora < _bloqueado_ate and _cache is None:
            raise RuntimeError("Open-Meteo em cooldown por limite de chamadas")
        try:
            _cache = _coletar()
            _cache_em = time.time()
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 429:
                _bloqueado_ate = time.time() + COOLDOWN_429
            if _cache is not None and agora - _cache_em < TTL_EMERGENCIA:
                idade = int((agora - _cache_em) / 60)
                print(f"[dados] Open-Meteo falhou ({exc}); "
                      f"servindo cache de {idade} min atras.")
                return _cache
            raise
        return _cache


def previsao_do_local(local: dict) -> dict | None:
    """Previsao de um ponto, com MET Norway como ultima tentativa."""
    try:
        tabela = previsao()
    except Exception as exc:
        print(f"[dados] coleta em lote falhou ({exc}); tentando MET Norway.")
        tabela = {}
    achado = tabela.get(local.get("id"))
    if achado:
        return achado
    if local.get("latitude") is None:
        return None
    try:
        return _met_no(local)
    except Exception as exc:
        print(f"[dados] MET Norway falhou para {local.get('id')}: {exc}")
        return None


def invalidar_cache() -> None:
    """Usado pelos testes e pelo endpoint de manutencao."""
    global _cache, _cache_em, _bloqueado_ate
    with _trava:
        _cache, _cache_em, _bloqueado_ate = None, 0.0, 0.0


def estado() -> dict:
    idade = int(time.time() - _cache_em) if _cache_em else None
    return {"pontos_em_cache": len(_cache or {}), "cache_idade_s": idade}

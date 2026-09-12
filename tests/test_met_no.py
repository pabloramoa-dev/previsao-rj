"""Provedor independente MET Norway.

O que estes testes protegem: a traducao para o formato interno nao inventa
numero, o horario UTC vira horario local antes de qualquer comparacao, e a
met.no de fato entra no calculo de concordancia entre provedores (secao 5.2).

A fixture reproduz o formato do endpoint `compact`, conferido contra a API viva:
`properties.timeseries[].data.instant.details` com air_temperature,
cloud_area_fraction, wind_speed (m/s) e `next_1_hours` com symbol_code e
precipitation_amount. Rajada, probabilidade de chuva e UV nao existem nesta
latitude — e isso e parte do que se testa aqui.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.previsao_rj import config
from src.previsao_rj.collectors import met_no
from src.previsao_rj.collectors.base import SourceResult
from src.previsao_rj.normalizers import snapshot as snap
from src.previsao_rj.quality import confidence as conf

SIMBOLOS = ["clearsky_night", "fair_day", "partlycloudy_day", "cloudy",
            "lightrain", "rain", "heavyrain", "rainandthunder"]


def _resposta_met_no(horas: int = 48) -> dict:
    """Resposta sintetica no formato do endpoint `compact`.

    Construida em codigo, e nao guardada como blob, para que a forma fique
    legivel na revisao: e exatamente a estrutura conferida contra a API viva —
    `instant.details` com air_temperature, cloud_area_fraction e wind_speed em
    m/s, e `next_1_hours` com symbol_code e precipitation_amount. Note o que
    NAO existe: rajada, probabilidade de chuva e UV.

    Comeca as 02:00Z de proposito: no Rio isso e 23:00 do dia anterior, o que
    exercita a conversao de fuso na virada do dia.
    """
    inicio = datetime(2026, 9, 12, 2, 0, tzinfo=timezone.utc)
    serie = []
    for i in range(horas):
        instante = inicio + timedelta(hours=i)
        temperatura = 19.0 + 7.0 * (1 - abs(((i % 24) - 14) / 14))
        serie.append({
            "time": instante.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {
                "instant": {"details": {
                    "air_pressure_at_sea_level": 1013.2,
                    "air_temperature": round(temperatura, 1),
                    "cloud_area_fraction": float(20 + (i % 5) * 15),
                    "relative_humidity": float(70 + (i % 4) * 5),
                    "wind_from_direction": float((i * 13) % 360),
                    "wind_speed": round(2.0 + (i % 6) * 0.7, 1),
                }},
                "next_1_hours": {
                    "summary": {"symbol_code": SIMBOLOS[i % len(SIMBOLOS)]},
                    "details": {"precipitation_amount": round(0.4 * (i % 7 == 0), 1)},
                },
            },
        })
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-43.1822, -22.9711, 2]},
        "properties": {
            "meta": {"updated_at": "2026-09-12T01:30:00Z",
                     "units": {"air_temperature": "celsius", "wind_speed": "m/s",
                               "precipitation_amount": "mm", "cloud_area_fraction": "%"}},
            "timeseries": serie,
        },
    }


@pytest.fixture(scope="module")
def bruto() -> dict:
    return _resposta_met_no()


@pytest.fixture(scope="module")
def traduzido(bruto) -> dict:
    return met_no.to_open_meteo_shape(bruto)


# --- simbolo -> codigo WMO -------------------------------------------------

@pytest.mark.parametrize("simbolo, esperado", [
    ("clearsky_day", 0),
    ("clearsky_night", 0),
    ("fair_polartwilight", 1),
    ("partlycloudy_day", 2),
    ("cloudy", 3),
    ("fog", 45),
    ("lightrain", 61),
    ("rain", 63),
    ("heavyrain", 65),
    ("heavyrainshowers_day", 82),
])
def test_simbolo_vira_codigo_wmo(simbolo, esperado):
    assert met_no.symbol_to_weather_code(simbolo) == esperado


def test_trovoada_vence_a_chuva():
    """'rainandthunder' e chuva, mas quem muda a pauta e o raio."""
    assert met_no.symbol_to_weather_code("rainandthunder") == 95
    assert met_no.symbol_to_weather_code("heavyrainandthunder_day") == 95


def test_simbolo_desconhecido_nao_vira_chute():
    assert met_no.symbol_to_weather_code("coisa_que_nao_existe") is None
    assert met_no.symbol_to_weather_code(None) is None
    assert met_no.symbol_to_weather_code("") is None


# --- traducao para o formato interno ---------------------------------------

def test_horario_utc_vira_local(traduzido):
    """02:00Z e 23:00 do dia anterior no Rio: sem isso os provedores nao alinham."""
    assert traduzido["hourly"]["time"][0] == "2026-09-11T23:00"
    assert traduzido["daily"]["time"][0] == "2026-09-11"


def test_formato_do_horario_e_o_mesmo_do_open_meteo(traduzido):
    for instante in traduzido["hourly"]["time"]:
        assert len(instante) == 16 and instante[10] == "T"


def test_vento_convertido_de_ms_para_kmh(traduzido):
    # fixture: 2.0 m/s no primeiro ponto -> 7.2 km/h
    assert traduzido["hourly"]["wind_speed_10m"][0] == pytest.approx(7.2, abs=0.05)


def test_dia_resume_maxima_minima_e_chuva(traduzido):
    dia = traduzido["daily"]
    i = dia["time"].index("2026-09-12")
    assert dia["temperature_2m_max"][i] > dia["temperature_2m_min"][i]
    assert dia["precipitation_sum"][i] >= 0


def test_dia_fica_com_o_tempo_mais_severo(traduzido):
    """O resumo do dia e o que decide a pauta, entao vale o pior codigo do dia."""
    dia = traduzido["daily"]
    i = dia["time"].index("2026-09-12")
    horas = [c for t, c in zip(traduzido["hourly"]["time"],
                               traduzido["hourly"]["weather_code"])
             if t.startswith("2026-09-12") and c is not None]
    assert dia["weather_code"][i] == max(horas)


def test_campo_que_a_met_no_nao_tem_fica_AUSENTE_e_nao_zero(traduzido):
    """Zero mentiria: 0% de chance de chuva e 0 km/h de rajada sao afirmacoes."""
    for ausente in ("wind_gusts_10m_max", "precipitation_probability_max", "uv_index_max",
                    "apparent_temperature_max"):
        assert ausente not in traduzido["daily"]
    for ausente in ("wind_gusts_10m", "precipitation_probability", "apparent_temperature"):
        assert ausente not in traduzido["hourly"]


def test_traducao_de_payload_vazio_nao_explode():
    vazio = met_no.to_open_meteo_shape({})
    assert vazio["daily"]["time"] == [] and vazio["hourly"]["time"] == []


# --- coleta ----------------------------------------------------------------

class _SessaoFake:
    """Session minima: devolve a fixture, ou falha nos pontos pedidos."""

    def __init__(self, bruto, falhar_em=()):
        self.bruto = bruto
        self.falhar_em = set(falhar_em)
        self.chamadas = []
        self.headers_vistos = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.chamadas.append(params)
        self.headers_vistos.append(headers)
        if params["lat"] in self.falhar_em:
            raise RuntimeError("ponto indisponivel")
        return _RespostaFake(self.bruto)


class _RespostaFake:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def sem_cache(tmp_path, monkeypatch):
    """Cache em disco isolado: um teste nao pode herdar coleta do outro."""
    monkeypatch.setattr("src.previsao_rj.collectors.base.CACHE_DIR", tmp_path / "cache")


@pytest.fixture
def sem_espera(monkeypatch):
    """Neutraliza o backoff entre tentativas.

    O que se testa aqui e o TRATAMENTO da falha, nao a duracao da espera. Sem
    isto, oito pontos falhando custam mais de um minuto de suite — e uma suite
    lenta e uma suite que ninguem roda.
    """
    monkeypatch.setattr("src.previsao_rj.collectors.base.time.sleep", lambda _s: None)


def test_coleta_um_ponto_por_local(bruto, sem_cache):
    locais = config.locations_by_tier(1)
    sessao = _SessaoFake(bruto)
    resultado = met_no.fetch(locais, session=sessao)
    assert resultado.status == "ok"
    assert len(sessao.chamadas) == len(locais)
    assert set(resultado.payload["points"]) == {l["id"] for l in locais}
    assert resultado.payload["model"] == "met_no"


def test_coleta_envia_user_agent_exigido_pela_met_no(bruto, sem_cache):
    locais = config.locations_by_tier(1)[:1]
    sessao = _SessaoFake(bruto)
    met_no.fetch(locais, session=sessao)
    enviado = sessao.headers_vistos[0]
    assert enviado and "User-Agent" in enviado
    assert "previsao-rj" in enviado["User-Agent"]


def test_ponto_que_falha_nao_derruba_a_coleta(bruto, sem_cache, sem_espera):
    locais = config.locations_by_tier(1)
    alvo = f"{locais[0]['latitude']:.4f}"
    resultado = met_no.fetch(locais, session=_SessaoFake(bruto, falhar_em=[alvo]))
    assert resultado.status == "ok"
    assert locais[0]["id"] not in resultado.payload["points"]
    assert locais[0]["id"] in resultado.detail


def test_coleta_sem_nenhum_ponto_vira_failed(bruto, sem_cache, sem_espera):
    locais = config.locations_by_tier(1)
    todos = [f"{l['latitude']:.4f}" for l in locais]
    resultado = met_no.fetch(locais, session=_SessaoFake(bruto, falhar_em=todos))
    assert resultado.status == "failed"
    assert not resultado.usable


def test_amostra_vazia_e_not_collected(sem_cache):
    assert met_no.fetch([]).status == "not_collected"


# --- efeito no snapshot e na confianca -------------------------------------

def _resultado_met_no(bruto, locais, dias):
    """Traduz a fixture e reetiqueta as datas para o dia do snapshot em teste."""
    traduzido = met_no.to_open_meteo_shape(bruto)
    de_para = dict(zip(traduzido["daily"]["time"], dias))
    traduzido["daily"]["time"] = [de_para.get(d, d) for d in traduzido["daily"]["time"]]
    traduzido["hourly"]["time"] = [de_para.get(t[:10], t[:10]) + t[10:]
                                   for t in traduzido["hourly"]["time"]]
    return SourceResult(name="met_no_forecast:met_no", status="ok",
                        payload={"model": "met_no",
                                 "points": {l["id"]: traduzido for l in locais}})


def test_met_no_entra_na_concordancia_entre_provedores(collected, tier1_locations, bruto):
    base = snap.build(dict(collected), tier1_locations)
    dias = [base["forecast"]["today"]["date"], base["forecast"]["tomorrow"]["date"]]

    com_metno = dict(collected)
    com_metno["met_no"] = _resultado_met_no(bruto, tier1_locations, dias)
    depois = snap.build(com_metno, tier1_locations)

    antes_modelos = base["forecast"]["today"]["locations"][0]["agreement"]["models_used"]
    depois_modelos = depois["forecast"]["today"]["locations"][0]["agreement"]["models_used"]
    assert depois_modelos == antes_modelos + 1
    assert "met_no" in depois["forecast"]["models"]


def test_met_no_aparece_na_procedencia_das_fontes(collected, tier1_locations, bruto):
    com_metno = dict(collected)
    com_metno["met_no"] = _resultado_met_no(bruto, tier1_locations, ["2026-09-11", "2026-09-12"])
    documento = snap.build(com_metno, tier1_locations)
    nomes = [s["name"] for s in documento["sources"]]
    assert "met_no_forecast:met_no" in nomes


def test_met_no_nao_contribui_para_a_concordancia_de_chuva():
    """Sem probabilidade de chuva, ela entra so na parte de temperatura."""
    por_modelo = {
        "ecmwf_ifs025": {"max_c": 30.0, "rain_probability_pct": 40},
        "icon_seamless": {"max_c": 31.0, "rain_probability_pct": 45},
        "met_no": {"max_c": 30.5, "rain_probability_pct": None},
    }
    _, nota = conf.model_agreement(por_modelo)
    assert "3 modelos" in nota


def test_met_no_vira_principal_se_o_open_meteo_inteiro_cair(collected, tier1_locations, bruto):
    """Rede de protecao: sem Open-Meteo utilizavel, o snapshot ainda sai."""
    caidos = {nome: SourceResult(name=nome, status="failed", detail="503")
              for nome in collected}
    caidos["met_no"] = _resultado_met_no(bruto, tier1_locations,
                                         ["2026-09-11", "2026-09-12"])
    documento = snap.build(caidos, tier1_locations)
    assert documento["forecast"]["primary_model"] == "met_no"
    assert documento["forecast"]["today"]["locations"]

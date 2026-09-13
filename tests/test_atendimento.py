# -*- coding: utf-8 -*-
"""Testes do atendimento por comentario, DM e voz.

Nenhum teste vai a rede: a previsao e injetada e as chamadas a Meta sao
substituidas. O que se verifica aqui e o que pode responder errado para um
seguidor — bairro trocado, relato fantasma no radar, cortesia gasta duas vezes
e audio que passa batido.
"""
from __future__ import annotations

import pytest

from previsao_rj.atendimento import dados, interacao, radar, resposta, voz
from previsao_rj.atendimento.roupa import recomendar

PREVISAO = {
    "tmin": 21.0, "tmax": 33.0, "prob_chuva": 20.0, "rajada_kmh": 18.0,
    "uv": 11.0, "tmin_amanha": 22.0, "tmax_amanha": 29.0,
    "prob_chuva_amanha": 70.0, "rajada_kmh_amanha": 30.0, "uv_amanha": 7.0,
    "_fonte": "open_meteo",
}


@pytest.fixture(autouse=True)
def previsao_fixa(monkeypatch):
    monkeypatch.setattr(dados, "previsao_do_local", lambda local: dict(PREVISAO))
    yield


@pytest.fixture(autouse=True)
def radar_limpo():
    radar._MEMORIA.clear()
    radar._EVENTOS.clear()
    radar._EVENTOS_SET.clear()
    radar._CONTEXTOS.clear()
    yield


# ------------------------------------------------------- cadastro e coleta


def test_pontos_cobrem_o_cadastro_sem_praia_solta():
    pontos = dados.pontos()
    assert "copacabana" in pontos
    assert "maracana_estadio" in pontos
    # praia resolve para o bairro; nao pode virar ponto de coleta proprio
    assert all(not p.get("beach_only") for p in pontos.values())
    assert len(pontos) >= 45


def test_todo_ponto_tem_coordenada():
    for pid, ponto in dados.pontos().items():
        assert ponto.get("latitude") is not None, pid
        assert ponto.get("longitude") is not None, pid


# ------------------------------------------------------------- previsao


def test_previsao_de_bairro_traz_hoje_e_amanha():
    texto, deu, local = resposta.montar("copacabana", True)
    assert deu is True
    assert local["id"] == "copacabana"
    assert "Hoje" in texto and "Amanha" in texto
    assert "Zona Sul" in texto


def test_pedido_conversacional_ainda_encontra_o_bairro():
    texto, deu, local = resposta.montar(
        "oi bom dia, como vai estar o tempo na tijuca hoje?", True)
    assert deu is True
    assert local["zone"] == "grande_tijuca"


def test_praia_entra_com_leitura_de_praia_e_uv():
    texto, deu, _ = resposta.montar("ipanema", True)
    assert deu is True
    assert "Praia:" in texto
    assert "UV extremo" in texto


def test_centro_pergunta_o_municipio_e_nao_chuta():
    texto, deu, local = resposta.montar("centro", True)
    assert deu is False
    assert local is None
    assert "Niter" in texto and "Rio de Janeiro" in texto


def test_lugar_de_fora_do_mapa_nao_inventa_previsao():
    texto, deu, _ = resposta.montar("juiz de fora", True)
    assert deu is False
    assert "Nao achei" in texto


def test_nao_seguidor_recebe_convite_no_fecho():
    texto, _, _ = resposta.montar("madureira", False)
    assert "por conta da casa" in texto
    seguidor, _, _ = resposta.montar("madureira", True)
    assert "por conta da casa" not in seguidor


def test_microclima_avisa_o_limite_do_modelo():
    texto, _, _ = resposta.montar("alto da boa vista", True)
    assert "Microclima" in texto


def test_previsao_indisponivel_nao_gasta_cortesia(monkeypatch):
    monkeypatch.setattr(dados, "previsao_do_local", lambda local: None)
    texto, deu, _ = resposta.montar("copacabana", False)
    assert deu is False
    assert "indispon" in texto


# ---------------------------------------------------------------- radar


def test_condicao_simples_so_aceita_relato_de_verdade():
    assert interacao.condicao_simples("chuva") == "chuva"
    assert interacao.condicao_simples("ta chovendo aqui") == "chuva"
    assert interacao.condicao_simples("vai ter chuva amanha?") is None
    assert interacao.condicao_simples("chuva ou sol?") is None


def test_relato_com_local_no_texto():
    assert interacao.condicao_no_texto("chuva forte no meier") == "chuva"
    assert "meier" in interacao.sem_condicao("chuva forte no meier")


def test_radar_conta_uma_vez_por_mensagem():
    assert radar.registrar("m1", "u1", "Zona Norte", "Meier", "chuva") is True
    assert radar.registrar("m1", "u1", "Zona Norte", "Meier", "chuva") is False
    assert "Meier" in radar.resumo("Zona Norte")


def test_radar_sem_relato_convida_em_vez_de_mentir():
    assert "Ainda nao ha relato" in radar.resumo("Zona Sul")


def test_contexto_expira_e_nao_vaza_id():
    radar.guardar_contexto("u9", "Zona Sul", "copacabana", "Copacabana")
    assert radar.obter_contexto("u9") == ("Zona Sul", "copacabana", "Copacabana")
    assert radar.obter_contexto("u8") is None
    assert "u9" not in str(radar._CONTEXTOS)


# ------------------------------------------------------------------ voz


def test_url_do_audio_encontra_anexo_de_voz():
    mensagem = {"attachments": [{"type": "audio",
                                 "payload": {"url": "https://x/y.mp4"}}]}
    assert voz.url_do_audio(mensagem) == "https://x/y.mp4"
    assert voz.url_do_audio({"attachments": [{"type": "image"}]}) is None
    assert voz.url_do_audio({}) is None


def test_transcricao_sem_chave_nao_quebra(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert voz.habilitada() is False
    assert voz.transcrever("https://x/y.mp4") is None


def test_audio_grande_e_descartado(monkeypatch):
    class RespostaFalsa:
        status_code = 200

        def iter_content(self, tamanho):
            yield b"0" * (voz.TAMANHO_MAX + 1)

    monkeypatch.setenv("GROQ_API_KEY", "teste")
    monkeypatch.setattr(voz.requests, "get", lambda *a, **k: RespostaFalsa())
    assert voz.transcrever("https://x/y.mp4") is None


# ------------------------------------------------------------ decisao


def test_decisao_muda_com_chuva_e_vento():
    assert "guarda-chuva" in recomendar(22, 30, 80, 10)
    assert "capa de chuva" in recomendar(22, 30, 80, 60)
    assert "casaco" in recomendar(12, 19, 10, 5)


def test_limpeza_do_pedido_tira_mencao_e_prefixo():
    assert interacao.limpar_pedido("@previsaorj previsao de Bangu") == "Bangu"
    assert interacao.limpar_pedido("tempo em Niteroi") == "Niteroi"


# ------------------------------------------------- coleta em lote (offline)


def test_coleta_em_lote_divide_e_mapeia_por_id(monkeypatch):
    """A rede nao e tocada: o que se verifica e o lote e o casamento id -> ponto."""
    chamadas: list[dict] = []

    class RespostaFalsa:
        status_code = 200

        def __init__(self, quantidade):
            self.quantidade = quantidade

        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "daily": {
                    "temperature_2m_min": [19.0, 20.0],
                    "temperature_2m_max": [30.0, 28.0],
                    "precipitation_probability_max": [10.0, 80.0],
                    "wind_gusts_10m_max": [22.0, 33.0],
                    "uv_index_max": [9.0, 6.0],
                }
            } for _ in range(self.quantidade)]

    def get_falso(url, params=None, timeout=None, **kwargs):
        chamadas.append(params)
        return RespostaFalsa(len(params["latitude"].split(",")))

    monkeypatch.setattr(dados.requests, "get", get_falso)
    dados.invalidar_cache()
    tabela = dados.previsao()

    assert len(chamadas) == (len(dados.pontos()) + dados.LOTE - 1) // dados.LOTE
    assert all(len(c["latitude"].split(",")) <= dados.LOTE for c in chamadas)
    assert set(tabela) == set(dados.pontos())
    assert tabela["copacabana"]["prob_chuva_amanha"] == 80.0
    assert tabela["copacabana"]["_fonte"] == "open_meteo"
    dados.invalidar_cache()


def test_campo_nulo_do_open_meteo_nao_vira_erro(monkeypatch):
    class RespostaFalsa:
        status_code = 200

        def __init__(self, quantidade):
            self.quantidade = quantidade

        def raise_for_status(self):
            return None

        def json(self):
            return [{"daily": {"temperature_2m_min": [None],
                               "temperature_2m_max": [None]}}
                    for _ in range(self.quantidade)]

    monkeypatch.setattr(
        dados.requests, "get",
        lambda url, params=None, timeout=None, **k: RespostaFalsa(
            len(params["latitude"].split(","))))
    dados.invalidar_cache()
    tabela = dados.previsao()
    assert tabela["copacabana"]["tmin"] == 0.0
    dados.invalidar_cache()


def test_cache_velho_e_servido_quando_a_api_cai(monkeypatch):
    dados.invalidar_cache()
    dados._cache = {"copacabana": dict(PREVISAO)}
    import time
    # 1h atras: velho para o TTL normal, valido para o TTL de emergencia
    dados._cache_em = time.time() - 3600

    def cai(*a, **k):
        raise dados.requests.RequestException("sem rede")

    monkeypatch.setattr(dados.requests, "get", cai)
    assert dados.previsao()["copacabana"]["tmax"] == 33.0
    dados.invalidar_cache()

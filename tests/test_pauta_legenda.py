"""A pauta manda no video, na legenda e na fila — ou nao manda em nada.

O primeiro Reel real (13/09/2026) foi ao ar com um formato e a fila registrou
outro. Estes testes prendem o contrato que impede isso de acontecer de novo:
quem escolhe e o `escolher_pauta`, uma vez so, e a legenda obedece ao item
escolhido.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.previsao_rj.publish import state
from src.previsao_rj.publish.caption import build_caption

FUTURO = "2099-01-01T00:00:00-03:00"


def item(**campos):
    base = {
        "format": "rio_antes_de_sair",
        "topic": "resumo",
        "location_ids": ["barra_da_tijuca", "copacabana"],
        "facts": {
            "barra_da_tijuca": {"max_c": 28, "rain_probability_pct": 30,
                                "wind_gust_max_kmh": 41},
            "copacabana": {"max_c": 27, "rain_probability_pct": 25,
                           "wind_gust_max_kmh": 34},
        },
        "extra": {},
        "total": 17,
        "character": "bira",
        "dedupe_key": "chave-de-teste",
        "status": "ready",
        "expires_at": FUTURO,
        "confidence": 65.0,
        "language": "forecast",
    }
    base.update(campos)
    return base


# ---------------------------------------------------------------- legenda


def test_legenda_sem_pauta_mantem_texto_antigo(snapshot):
    legenda = build_caption(snapshot)
    assert "contrastes importantes" in legenda
    assert "@previsaorj" in legenda


@pytest.mark.parametrize("formato", ["rio_antes_de_sair", "chove_onde",
                                     "fim_de_semana", "vai_dar_praia",
                                     "vai_ao_jogo"])
def test_toda_legenda_tem_assinatura_e_hashtag(snapshot, formato):
    """Sem a assinatura o `publish.cli` bloqueia a publicacao — e bem assim."""
    legenda = build_caption(snapshot, item(format=formato))
    assert "@previsaorj" in legenda.casefold()
    assert "#PrevisaoRJ" in legenda
    assert "None" not in legenda
    assert "{" not in legenda


def test_legenda_de_contraste_usa_as_duas_pontas(snapshot):
    pauta = item(format="chove_onde", topic="chuva",
                 location_ids=["tijuca", "icarai"],
                 extra={"contrast": {"spread": 37.0,
                                     "high": {"id": "tijuca", "name": "Tijuca",
                                              "value": 57.0},
                                     "low": {"id": "icarai", "name": "Icaraí",
                                             "value": 20.0}}})
    legenda = build_caption(snapshot, pauta)
    assert "Tijuca" in legenda and "Icaraí" in legenda
    assert "57%" in legenda and "20%" in legenda
    assert "37" in legenda


def test_janela_de_chuva_fala_de_chuva_e_nao_de_temperatura(snapshot):
    """O bug de 15/09/2026, preso em teste.

    A pauta `janela_chuva` não tem bloco de contraste e o volume de chuva não
    está em `facts` — só no snapshot. A primeira versão caiu num campo padrão e
    publicou a MÁXIMA rotulada como se fosse a previsão de chuva: "Barra da
    Tijuca: previsão de 22". Vinte e dois graus, anunciados numa pauta de chuva.
    """
    chuvoso = {
        'forecast': {'today': {'date': '2026-09-15', 'locations': [
            {'id': 'barra_da_tijuca', 'name': 'Barra da Tijuca', 'max_c': 22,
             'rain_mm': 1.6, 'rain_window': {'start': '15:00', 'end': '18:00'}},
            {'id': 'campo_grande', 'name': 'Campo Grande', 'max_c': 22,
             'rain_mm': 1.5, 'rain_window': {'start': '16:00', 'end': '19:00'}},
        ]}}}
    pauta = item(format="chove_onde", topic="janela_chuva",
                 location_ids=["barra_da_tijuca", "campo_grande"],
                 facts={}, extra={})
    legenda = build_caption(chuvoso, pauta)
    assert "1.6 mm" in legenda and "1.5 mm" in legenda
    assert "15:00" in legenda and "18:00" in legenda
    assert "22" not in legenda, "máxima não entra em pauta de chuva"


def test_sem_o_dado_do_topico_volta_ao_resumo_do_dia(snapshot):
    """Faltando o campo da pauta, a legenda vira o resumo geral do dia — com o
    número dito pelo que ele é. O que não pode é a máxima aparecer vestida de
    volume de chuva."""
    sem_chuva = {
        'forecast': {'today': {'date': '2026-09-15', 'locations': [
            {'id': 'tijuca', 'name': 'Tijuca', 'max_c': 31,
             'wind_gust_max_kmh': 28},
        ]}}}
    pauta = item(format="chove_onde", topic="janela_chuva",
                 location_ids=["tijuca"], facts={}, extra={})
    legenda = build_caption(sem_chuva, pauta)
    assert "mm" not in legenda
    assert "volume previsto" not in legenda
    assert "Máximas entre" in legenda and "31°" in legenda
    assert "@previsaorj" in legenda


def test_unidade_acompanha_o_topico_no_contraste(snapshot):
    pauta = item(format="chove_onde", topic="vento",
                 location_ids=["campo_grande", "duque_de_caxias"],
                 extra={"contrast": {"spread": 15.0,
                                     "high": {"id": "campo_grande",
                                              "name": "Campo Grande", "value": 34.0},
                                     "low": {"id": "duque_de_caxias",
                                             "name": "Duque de Caxias", "value": 19.0}}})
    legenda = build_caption(snapshot, pauta)
    assert "34 km/h" in legenda and "19 km/h" in legenda
    assert "15 km/h de diferença" in legenda


def test_legenda_de_fim_de_semana_mostra_os_dois_dias(snapshot):
    pauta = item(format="fim_de_semana", topic="fim_de_semana",
                 extra={"dates": ["2026-09-12", "2026-09-13"],
                        "forecast": {
                            "2026-09-12": [{"id": "tijuca", "max_c": 30,
                                            "rain_probability_pct": 57}],
                            "2026-09-13": [{"id": "copacabana", "max_c": 27,
                                            "rain_probability_pct": 25}]}})
    legenda = build_caption(snapshot, pauta)
    assert "12/09" in legenda and "13/09" in legenda
    assert "Tijuca" in legenda


def test_legenda_cai_para_o_resumo_quando_a_pauta_nao_tem_dado(snapshot):
    """Coleta incompleta encurta a legenda; nunca produz campo vazio."""
    pauta = item(format="chove_onde", topic="chuva", location_ids=[],
                 facts={}, extra={})
    legenda = build_caption(snapshot, pauta)
    assert "Máximas entre" in legenda
    assert "@previsaorj" in legenda


def test_formatos_diferentes_geram_legendas_diferentes(snapshot):
    """Se duas pautas dessem a mesma legenda, o veto de duplicata da Meta
    barraria a segunda publicacao sem ninguem entender por que."""
    a = build_caption(snapshot, item(format="rio_antes_de_sair"))
    b = build_caption(snapshot, item(format="fim_de_semana",
                                     extra={"dates": ["2026-09-12"],
                                            "forecast": {"2026-09-12": [
                                                {"id": "tijuca", "max_c": 30}]}}))
    assert a != b


# ---------------------------------------------------- trava do dia na fila


def test_published_on_encontra_a_publicacao_do_dia(tmp_path):
    fila = tmp_path / "fila.json"
    state.save(fila, [item(status="published",
                           published_at="2026-09-13T12:16:20-03:00",
                           media_id="123")])
    assert state.published_on(fila, "2026-09-13")["media_id"] == "123"
    assert state.published_on(fila, "2026-09-14") is None


def test_published_on_ignora_item_apenas_reivindicado(tmp_path):
    """`publishing` nao e publicacao: a trava do dia nao pode travar por ele."""
    fila = tmp_path / "fila.json"
    state.save(fila, [item(status="publishing",
                           claimed_at="2026-09-13T12:15:00-03:00")])
    assert state.published_on(fila, "2026-09-13") is None


# ------------------------------------------------------- escolher_pauta.py


def escolher(tmp_path, fila, *extras):
    saida = tmp_path / "github_output"
    saida.touch()
    processo = subprocess.run(
        [sys.executable, "-m", "scripts.escolher_pauta",
         "--queue", str(fila), "--out", str(tmp_path / "pauta.json"), *extras],
        capture_output=True, text=True, cwd=Path.cwd(),
        env={**__import__("os").environ, "GITHUB_OUTPUT": str(saida)})
    return processo, dict(
        linha.split("=", 1) for linha in saida.read_text().splitlines() if "=" in linha)


def test_escolher_pauta_publica_o_melhor_item_pronto(tmp_path):
    fila = tmp_path / "fila.json"
    state.save(fila, [item(dedupe_key="fraco", total=10),
                      item(dedupe_key="forte", total=22, character="bia",
                           format="fim_de_semana")])
    processo, saidas = escolher(tmp_path, fila)
    assert processo.returncode == 0, processo.stderr
    assert saidas["seguir"] == "sim"
    assert saidas["dedupe_key"] == "forte"
    assert saidas["formato"] == "fim_de_semana"
    assert saidas["personagem"] == "bia"
    gravado = json.loads((tmp_path / "pauta.json").read_text(encoding="utf-8"))
    assert gravado["dedupe_key"] == "forte"


def test_escolher_pauta_trava_quando_ja_publicou_hoje(tmp_path):
    """A trava que permite agendar varias tentativas de cron por dia."""
    from src.previsao_rj.collectors.base import now
    fila = tmp_path / "fila.json"
    state.save(fila, [item(dedupe_key="ja-foi", status="published",
                           published_at=now().isoformat(), media_id="9"),
                      item(dedupe_key="pronto")])
    processo, saidas = escolher(tmp_path, fila, "--exigir-inedito-hoje")
    assert processo.returncode == 0, processo.stderr
    assert saidas["seguir"] == "nao"
    assert saidas["motivo"] == "ja_publicado_hoje"
    assert not (tmp_path / "pauta.json").exists()


def test_escolher_pauta_sem_item_pronto_nao_quebra_o_workflow(tmp_path):
    fila = tmp_path / "fila.json"
    state.save(fila, [item(status="blocked", vetoes=["sem_dado"])])
    processo, saidas = escolher(tmp_path, fila)
    assert processo.returncode == 0, processo.stderr
    assert saidas["seguir"] == "nao"
    assert saidas["motivo"] == "sem_pauta_pronta"


def test_escolher_pauta_ignora_item_vencido(tmp_path):
    fila = tmp_path / "fila.json"
    state.save(fila, [item(expires_at="2020-01-01T00:00:00-03:00")])
    _, saidas = escolher(tmp_path, fila)
    assert saidas["seguir"] == "nao"

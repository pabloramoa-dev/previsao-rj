"""A voz diz a hora por extenso; a tela mostra a forma curta.

Caso que originou o teste: Reel manual de 15/09/2026 (execução 35037630591).
O roteiro levava "entre 20:00 e 23:00" e o Kokoro leu "vinte e três zero zero".
"""
from __future__ import annotations

import re

import pytest

from src.previsao_rj.editorial import formats
from src.previsao_rj.editorial.engine import evaluate
from src.previsao_rj.editorial.script import (faixa_escrita, faixa_falada,
                                               hora_escrita, pico_escrito,
                                               pico_falado)

HORA_DIGITAL = re.compile(r"\d{1,2}:\d{2}")


@pytest.mark.parametrize("inicio, fim, falada, escrita", [
    ("20:00", "23:00", "das vinte às vinte e três horas", "das 20h às 23h"),
    ("21:00", "23:00", "das vinte e uma às vinte e três horas", "das 21h às 23h"),
    ("01:00", "04:00", "da uma às quatro horas", "da 1h às 4h"),
    ("00:00", "03:00", "da meia-noite às três horas", "da meia-noite às 3h"),
    ("11:00", "12:00", "das onze horas ao meio-dia", "das 11h ao meio-dia"),
    ("12:00", "15:00", "do meio-dia às quinze horas", "do meio-dia às 15h"),
    ("19:30", "22:00", "das dezenove e trinta às vinte e duas horas", "das 19h30 às 22h"),
])
def test_faixa(inicio, fim, falada, escrita):
    assert faixa_falada(inicio, fim) == falada
    assert faixa_escrita(inicio, fim) == escrita


@pytest.mark.parametrize("hora, falada, escrita", [
    ("19:00", "por volta das dezenove horas", "por volta das 19h"),
    ("01:00", "por volta da uma hora", "por volta da 1h"),
    ("02:00", "por volta das duas horas", "por volta das 2h"),
    ("22:00", "por volta das vinte e duas horas", "por volta das 22h"),
    ("12:00", "por volta do meio-dia", "por volta do meio-dia"),
    ("00:00", "por volta da meia-noite", "por volta da meia-noite"),
])
def test_pico(hora, falada, escrita):
    assert pico_falado(hora) == falada
    assert pico_escrito(hora) == escrita


def test_hora_invalida_nao_quebra():
    assert hora_escrita("sem hora") == "sem hora"
    assert faixa_falada("x", "y") == "entre x e y"
    assert pico_falado(None) == "por volta das None"


def _preparar_chuva(snapshot, monkeypatch, janelas):
    candidato = next(c for c in evaluate(snapshot)
                     if c["format"] == "chove_onde" and c["topic"] == "chuva")
    monkeypatch.setattr(formats, "evaluate", lambda *a, **k: [candidato])
    monkeypatch.setattr(formats, "hora_agora", lambda: 6)
    ids = candidato["location_ids"]
    for loc in snapshot["forecast"]["today"]["locations"]:
        if loc["id"] in ids:
            loc["rain_window"] = janelas[ids.index(loc["id"]) % len(janelas)]
    return formats.prepare(snapshot, "chove_onde")["beats"]


def test_roteiro_de_chuva_fala_hora_por_extenso(snapshot, monkeypatch):
    batidas = _preparar_chuva(snapshot, monkeypatch, [
        {"start": "20:00", "end": "23:00"},
        {"start": "00:00", "end": "23:00", "peak_hour": "19:00",
         "peak_probability_pct": 80},
    ])
    falas = " ".join(b["fala"] for b in batidas)
    legendas = " ".join(b["legenda"] for b in batidas)

    assert not HORA_DIGITAL.search(falas), falas
    assert "das vinte às vinte e três horas" in falas
    assert "por volta das dezenove horas" in falas
    assert "das 20h às 23h" in legendas and "por volta das 19h" in legendas
    assert not HORA_DIGITAL.search(legendas), legendas


def test_batida_sem_hora_mantem_legenda_igual_a_fala(snapshot, monkeypatch):
    batidas = _preparar_chuva(snapshot, monkeypatch, [{"start": "20:00", "end": "23:00"}])
    sem_hora = [b for b in batidas if "chuva é mais provável" not in b["fala"]]
    assert sem_hora
    assert all(b["legenda"] == b["fala"] for b in sem_hora)


# ----------------------------------------------- última passada antes da voz

from src.previsao_rj.editorial.script import decimal_br, para_voz  # noqa: E402


def test_para_voz_troca_ponto_decimal_e_hora_digital():
    # "3.1" o espeak lê "três um"; "23:00", "vinte e três zero zero".
    assert para_voz("volume de 3.1 milímetros") == "volume de 3,1 milímetros"
    assert para_voz("até 23:00") == "até vinte e três horas"
    assert para_voz("às 25:99") == "às 25:99"
    assert para_voz("Previsão RJ. Confira.") == "Previsão RJ. Confira."


def test_legenda_na_tela_usa_virgula():
    assert decimal_br("3.1 mm e 41.5 km/h") == "3,1 mm e 41,5 km/h"


def test_toda_fala_do_prepare_sai_sem_ponto_decimal(snapshot, monkeypatch):
    batidas = _preparar_chuva(snapshot, monkeypatch, [{"start": "20:00", "end": "23:00"}])
    for b in batidas:
        assert not re.search(r"\d\.\d", b["fala"]), b["fala"]
        assert not re.search(r"\d\.\d", b["legenda"]), b["legenda"]


def test_batida_aplica_voz_e_tela():
    b = formats.batida("Em Campo Grande, volume de 3.6 milímetros até 23:00.")
    assert b["fala"] == "Em Campo Grande, volume de 3,6 milímetros até vinte e três horas."
    assert b["legenda"] == "Em Campo Grande, volume de 3,6 milímetros até 23:00."

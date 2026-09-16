"""Na Tijuca, no Méier, em Copacabana — e nunca "Em Centro".

Caso que originou o teste: Reel manual 35042034124 (16/09/2026), que narrou
"Em Barra da Tijuca" e "Em Centro", e repetiu a mesma faixa de horário
bairro a bairro.
"""
from __future__ import annotations

import pytest

from src.previsao_rj import config
from src.previsao_rj.editorial import formats
from src.previsao_rj.editorial.engine import evaluate
from src.previsao_rj.geo.preposicao import em_local, em_locais


@pytest.mark.parametrize("nome, esperado", [
    ("Barra da Tijuca", "na Barra da Tijuca"),
    ("Tijuca", "na Tijuca"),
    ("Centro", "no Centro"),
    ("Méier", "no Méier"),
    ("Recreio dos Bandeirantes", "no Recreio dos Bandeirantes"),
    ("Copacabana", "em Copacabana"),
    ("Campo Grande", "em Campo Grande"),
    ("Niterói", "em Niterói"),
    ("Duque de Caxias", "em Duque de Caxias"),
    ("Barcas - Praça XV", "nas Barcas - Praça XV"),
])
def test_preposicao(nome, esperado):
    assert em_local(nome) == esperado


def test_maiuscula_no_inicio_da_frase():
    assert em_local("Centro", inicio=True) == "No Centro"
    assert em_local("Bangu", inicio=True) == "Em Bangu"


def test_lista_de_lugares():
    assert em_locais(["Barra da Tijuca"]) == "na Barra da Tijuca"
    assert em_locais(["Barra da Tijuca", "Campo Grande"]) == "na Barra da Tijuca e em Campo Grande"
    assert em_locais(["Centro", "Tijuca", "Bangu"], inicio=True) == "No Centro, na Tijuca e em Bangu"


def test_todo_lugar_cadastrado_tem_preposicao_valida():
    locais = config.locations_by_tier(99)
    assert locais
    for loc in locais:
        assert em_local(loc["name"]).split(" ", 1)[0] in {"na", "no", "nas", "em"}


def _batidas(snapshot, monkeypatch, janelas):
    candidato = next(c for c in evaluate(snapshot)
                     if c["format"] == "chove_onde" and c["topic"] == "chuva")
    monkeypatch.setattr(formats, "evaluate", lambda *a, **k: [candidato])
    monkeypatch.setattr(formats, "hora_agora", lambda: 6)
    ids = candidato["location_ids"]
    locais = {l["id"]: l for l in snapshot["forecast"]["today"]["locations"]}
    for i, loc_id in enumerate(ids):
        locais[loc_id]["rain_window"] = janelas[i % len(janelas)]
    nomes = [locais[i]["name"] for i in ids[:3]]
    return formats.prepare(snapshot, "chove_onde")["beats"], nomes


def test_mesma_faixa_vira_uma_frase_so(snapshot, monkeypatch):
    batidas, nomes = _batidas(snapshot, monkeypatch, [{"start": "21:00", "end": "23:00"}])
    falas = [b["fala"] for b in batidas]
    faixa = [f for f in falas if "das vinte e uma às vinte e três horas" in f]
    assert len(faixa) == 1, falas
    assert faixa[0].startswith(em_locais(nomes, inicio=True) + ", a chuva é mais provável")


def test_faixas_diferentes_ficam_separadas(snapshot, monkeypatch):
    batidas, nomes = _batidas(snapshot, monkeypatch, [
        {"start": "21:00", "end": "23:00"},
        {"start": "14:00", "end": "17:00"},
    ])
    falas = " ".join(b["fala"] for b in batidas)
    assert falas.count("a chuva é mais provável") == 2
    assert "das catorze às dezessete horas" in falas


def test_fala_do_reel_nao_comeca_com_em_seguido_de_artigo(snapshot, monkeypatch):
    batidas, _ = _batidas(snapshot, monkeypatch, [{"start": "21:00", "end": "23:00"}])
    for b in batidas:
        for errado in ("Em Centro", "Em Barra", "Em Tijuca", "Em Méier"):
            assert errado not in b["fala"], b["fala"]

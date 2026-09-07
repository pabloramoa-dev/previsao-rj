"""Schema de snapshot — Plano Mestre, secoes 12.2, 5.3 e 17.3.

Criterio de saida da Fase 1: snapshot valido para Rio, Niteroi e Baixada, com
timestamps e confianca, e sem quebrar o que o render ja consome.
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest

from src.previsao_rj.collectors.base import SourceResult, now
from src.previsao_rj.normalizers import snapshot as snap

CAMPOS_DE_PROCEDENCIA = {"name", "status", "fetched_at", "model_run",
                         "valid_for", "fallback_used", "detail", "age_minutes"}

# Campos que o render (characters/pipeline.snapshot_beats), a legenda
# (publish/caption) e o editorial ja leem. Renomear qualquer um destes quebra
# o unico formato que hoje roda ponta a ponta.
CONTRATO_DO_RENDER = {"id", "name", "min_c", "max_c",
                      "rain_probability_pct", "rain_mm", "weather_code"}


def test_blocos_obrigatorios_do_plano(snapshot):
    for chave in ("schema_version", "generated_at", "timezone", "region", "coverage",
                  "forecast", "observed", "marine", "beach_status", "events",
                  "football", "mobility", "confidence", "sources"):
        assert chave in snapshot, f"bloco ausente: {chave}"
    assert snapshot["schema_version"] == "2.0"
    assert snapshot["forecast"]["today"]["date"] < snapshot["forecast"]["tomorrow"]["date"]


def test_cobre_rio_niteroi_e_baixada(snapshot):
    zonas = {e["zone"] for e in snapshot["forecast"]["today"]["locations"]}
    municipios = set(snapshot["coverage"])
    assert "rio_de_janeiro" in municipios and "niteroi" in municipios
    assert municipios & {"duque_de_caxias", "nova_iguacu"}
    assert {"zona_sul", "grande_tijuca", "baixada"} <= zonas


def test_contrato_com_o_render_preservado(snapshot):
    for entrada in snapshot["forecast"]["today"]["locations"]:
        assert CONTRATO_DO_RENDER <= set(entrada)
        assert isinstance(entrada["max_c"], int)
        assert isinstance(entrada["rain_probability_pct"], int)


def test_toda_fonte_declara_procedencia(snapshot):
    assert snapshot["sources"], "snapshot sem bloco de fontes"
    for fonte in snapshot["sources"]:
        assert CAMPOS_DE_PROCEDENCIA <= set(fonte)
        assert fonte["fetched_at"]


def test_cada_modelo_aparece_com_nome_proprio_nas_fontes(snapshot):
    nomes = {f["name"] for f in snapshot["sources"]}
    assert {"open_meteo_forecast:ecmwf_ifs025",
            "open_meteo_forecast:gfs_seamless",
            "open_meteo_forecast:icon_seamless"} <= nomes
    assert len(nomes) == len(snapshot["sources"]), "fonte repetida sem distincao"


def test_dispersao_entre_modelos_e_registrada(snapshot):
    entrada = next(e for e in snapshot["forecast"]["today"]["locations"]
                   if e["id"] == "tijuca")
    assert entrada["agreement"]["models_used"] == 3
    assert entrada["agreement"]["max_c_spread"] > 0
    assert entrada["agreement"]["rain_probability_spread_pct"] > 0
    assert set(entrada["models"]) == {"ecmwf_ifs025", "gfs_seamless", "icon_seamless"}


def test_janela_de_chuva_sai_do_dado_horario(snapshot):
    tijuca = next(e for e in snapshot["forecast"]["today"]["locations"]
                  if e["id"] == "tijuca")
    janela = tijuca["rain_window"]
    assert janela is not None
    assert janela["start"] < janela["end"]
    assert janela["peak_probability_pct"] >= janela["threshold_pct"]

    copacabana = next(e for e in snapshot["forecast"]["today"]["locations"]
                      if e["id"] == "copacabana")
    assert copacabana["rain_window"] is None, "dia seco nao deve inventar janela"


def test_dia_de_referencia_vem_do_dado_e_nao_do_relogio(snapshot, raw_open_meteo):
    assert snapshot["forecast"]["today"]["date"] == raw_open_meteo["_reference_day"]


def test_snapshot_e_deterministico(collected, tier1_locations):
    a = snap.build(collected, tier1_locations)
    b = snap.build(collected, tier1_locations)
    for doc in (a, b):
        doc.pop("generated_at"), doc.pop("confidence"), doc.pop("sources")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_observacao_desligada_aparece_como_nao_coletada(snapshot):
    assert snapshot["observed"]["status"] == "not_collected"
    assert snapshot["marine"]["status"] == "not_collected"
    assert snapshot["beach_status"]["status"] == "not_collected"


def test_promocao_de_modelo_secundario_marca_fallback(collected, tier1_locations):
    collected["ecmwf_ifs025"] = SourceResult("open_meteo_forecast:ecmwf_ifs025",
                                             "failed", detail="timeout simulado")
    documento = snap.build(collected, tier1_locations)
    assert documento["forecast"]["primary_model"] != "ecmwf_ifs025"
    assert documento["forecast"]["primary_model"] in {"gfs_seamless", "icon_seamless"}
    assert "ecmwf_ifs025" not in documento["forecast"]["models"]


def test_sem_nenhum_modelo_utilizavel_o_snapshot_falha_alto(collected, tier1_locations):
    for nome in list(collected):
        collected[nome] = SourceResult(f"open_meteo_forecast:{nome}", "failed",
                                       detail="rede")
    with pytest.raises(RuntimeError, match="nenhum modelo"):
        snap.build(collected, tier1_locations)


def test_gate_de_frescor_do_snapshot(snapshot):
    assert not snap.is_stale(snapshot, ttl_minutes=120)
    futuro = now() + timedelta(minutes=200)
    assert snap.is_stale(snapshot, ttl_minutes=120, reference=futuro)

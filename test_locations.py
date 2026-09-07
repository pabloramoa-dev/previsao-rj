"""Integridade do cadastro geografico — Plano Mestre, capitulo 4."""
from __future__ import annotations

import pytest

from src.previsao_rj import config

ZONAS_DO_PLANO = {
    "zona_sul", "grande_tijuca", "centro", "zona_norte", "jacarepagua",
    "barra_recreio", "zona_oeste", "niteroi_baia", "niteroi_oceanica", "baixada",
}


def test_as_dez_zonas_do_plano_existem():
    assert set(config.load_places()["zones"]) == ZONAS_DO_PLANO


def test_toda_zona_tem_pelo_menos_um_local():
    locations = config.load_places()["locations"]
    cobertas = {loc["zone"] for loc in locations}
    assert cobertas == ZONAS_DO_PLANO


def test_validacao_roda_e_nao_encontra_erro():
    # validate_places levanta ValueError em id duplicado, zona ou municipio
    # inexistente, coordenada fora do recorte e alias repetido.
    config.validate_places(config.load_places())


def test_amostra_do_reel_base_cobre_rio_niteroi_e_baixada():
    tier1 = config.locations_by_tier(1)
    municipios = {loc["municipality"] for loc in tier1}
    assert "rio_de_janeiro" in municipios
    assert "niteroi" in municipios
    assert municipios & {"duque_de_caxias", "nova_iguacu"}, "Baixada fora da amostra"
    assert len(tier1) >= 6


def test_amostra_e_deterministica():
    assert config.locations_by_tier(1) == config.locations_by_tier(1)
    ids = [loc["id"] for loc in config.locations_by_tier(1)]
    assert ids == sorted(ids, key=lambda i: i)


def test_tier_maior_contem_o_menor():
    ids1 = {loc["id"] for loc in config.locations_by_tier(1)}
    ids2 = {loc["id"] for loc in config.locations_by_tier(2)}
    assert ids1 < ids2


def test_estadios_dos_tres_formatos_de_jogo_estao_cadastrados():
    stadiums = {s["id"] for s in
                config.load_places()["points_of_interest"]["stadiums"]}
    assert stadiums == {"maracana_estadio", "nilton_santos", "sao_januario"}


def test_coordenada_de_local_invalida_e_recusada():
    dados = config.load_places()
    quebrado = {
        "zones": dados["zones"],
        "municipalities": dados["municipalities"],
        "locations": [dict(dados["locations"][0], latitude=-30.0)],
    }
    with pytest.raises(ValueError, match="latitude"):
        config.validate_places(quebrado)


def test_alias_repetido_entre_locais_e_recusado():
    dados = config.load_places()
    a, b = dados["locations"][0], dados["locations"][1]
    quebrado = {
        "zones": dados["zones"],
        "municipalities": dados["municipalities"],
        "locations": [dict(a, aliases=["mesmo alias"]), dict(b, aliases=["mesmo alias"])],
    }
    with pytest.raises(ValueError, match="repetido"):
        config.validate_places(quebrado)

"""Resolver geografico e banco de aliases — Plano Mestre, secao 4.4.

O plano exige que as correcoes de ambiguidade sejam testadas por fixtures.
"""
from __future__ import annotations

import pytest

from src.previsao_rj.geo.resolver import GeoResolver, normalize


@pytest.fixture(scope="module")
def resolver() -> GeoResolver:
    return GeoResolver()


def test_normaliza_acento_e_pontuacao():
    assert normalize("Icaraí!") == "icarai"
    assert normalize("  SÃO   Gonçalo ") == "sao goncalo"


@pytest.mark.parametrize("texto, esperado", [
    ("Tijuca", "tijuca"),
    ("tijuca", "tijuca"),
    ("Icaraí", "icarai"),
    ("icarai", "icarai"),
    ("copa", "copacabana"),
    ("Barra da Tijuca", "barra_da_tijuca"),
    ("nova iguaçu", "nova_iguacu"),
    ("Recreio dos Bandeirantes", "recreio"),
    ("madureira", "madureira"),
    ("itacoa", "itacoatiara"),
])
def test_aliases_resolvem_direto(resolver, texto, esperado):
    r = resolver.resolve(texto)
    assert r.resolved, f"{texto} nao resolveu: {r.status}"
    assert r.location["id"] == esperado


def test_icarai_aponta_niteroi(resolver):
    assert resolver.resolve("Icaraí").location["municipality"] == "niteroi"


@pytest.mark.parametrize("texto", ["Centro", "centro", "Barra", "Caxias", "Campo Grande"])
def test_ambiguos_perguntam_em_vez_de_chutar(resolver, texto):
    r = resolver.resolve(texto)
    assert r.status == "ambiguous", f"{texto} deveria pedir confirmacao"
    assert r.question and r.question.endswith("?")


def test_centro_resolve_quando_o_municipio_e_conhecido(resolver):
    assert resolver.resolve("Centro", municipality_hint="niteroi").location["id"] == "niteroi_centro"
    assert resolver.resolve("Centro", municipality_hint="rio_de_janeiro").location["id"] == "centro_rio"


def test_pergunta_de_centro_cita_os_dois_municipios(resolver):
    pergunta = normalize(resolver.resolve("Centro").question)
    assert "rio de janeiro" in pergunta and "niteroi" in pergunta


def test_nome_exibido_mantem_acento(resolver):
    # O nome vai para a legenda e para a tela: alias sem acento, nome com acento.
    assert resolver.resolve("icarai").location["name"] == "Icaraí"
    assert resolver.resolve("nova iguacu").location["name"] == "Nova Iguaçu"


def test_bairro_dentro_de_uma_frase(resolver):
    r = resolver.resolve("bom dia, como vai estar o tempo na tijuca hoje?")
    assert r.resolved and r.location["id"] == "tijuca"


def test_erro_de_digitacao_resolve_como_aproximado(resolver):
    r = resolver.resolve("madureria")
    assert r.resolved and r.location["id"] == "madureira"
    assert r.confidence == "aproximada"


def test_lugar_fora_da_cobertura_nao_inventa_resposta(resolver):
    for texto in ["Volta Redonda", "Belo Horizonte", "asdfgh"]:
        assert resolver.resolve(texto).status == "unknown"


def test_estadio_resolve_como_ponto_de_interesse(resolver):
    r = resolver.resolve("estadio do maracana")
    assert r.resolved and r.location["id"] == "maracana_estadio"


def test_texto_vazio_nao_quebra(resolver):
    assert resolver.resolve("").status == "unknown"
    assert resolver.resolve("   ").status == "unknown"

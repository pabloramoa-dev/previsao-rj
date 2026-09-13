"""Faixas verticais do quadro — o enquadramento como invariante, nao como sorte.

Estes testes existem por causa de tres defeitos reais vistos no primeiro
ensaio: o cartao de cidade invadindo a marca do perfil, a tabela das cinco
cidades por cima do selo, e o gancho cobrindo o rosto do apresentador nos
primeiros segundos — justamente onde a retencao se decide.

Nao importam manim de proposito: assim rodam no CI, que instala so
requirements/test.txt. As alturas usadas sao as medidas por
scripts/medir_layout.py.
"""
from __future__ import annotations

import pytest

from src.previsao_rj.render.characters import layout as LAY


def test_marca_fica_acima_de_qualquer_painel():
    """Nenhum cartao pode cobrir o @previsaorj.

    Quem chega por compartilhamento descobre o perfil por essa marca; cobri-la
    e perder a unica assinatura do video.
    """
    for nome, altura in LAY.ALTURAS.items():
        assert not LAY.cobre_marca(altura), f"{nome} invade a marca do perfil"


def test_painel_que_fica_com_o_apresentador_nao_cobre_o_rosto():
    """So pode cobrir o rosto quem tira o apresentador de cena."""
    for nome, altura in LAY.ALTURAS.items():
        if nome in LAY.SOZINHOS:
            continue
        assert not LAY.cobre_rosto(altura), f"{nome} cobre o rosto do apresentador"


def test_nenhum_painel_sai_da_area_visivel():
    for nome, altura in LAY.ALTURAS.items():
        assert not LAY.sai_da_tela(altura), f"{nome} passa da area que a camera enquadra"


def test_selo_nao_encosta_na_marca():
    topo_selo = LAY.Y_SELO + LAY.ALTURA_SELO / 2
    assert topo_selo < LAY.base_marca()


def test_painel_ancora_pela_borda_de_cima():
    """Cartao baixo e cartao alto comecam na mesma linha; so a base desce."""
    baixo = LAY.faixa_painel(LAY.ALTURAS["faixa"])
    alto = LAY.faixa_painel(LAY.ALTURAS["resumo"])
    assert baixo[1] == alto[1] == LAY.TOPO_PAINEL
    assert alto[0] < baixo[0]


# --- fusao das janelas de saida de cena ------------------------------------

def test_janelas_vizinhas_viram_uma_so():
    """Gancho e CTA colados: o apresentador sai uma vez, nao duas."""
    assert LAY.juntar_janelas([(22.0, 24.0), (24.0, 25.7)]) == [(22.0, 25.7)]


def test_janelas_separadas_continuam_separadas():
    assert LAY.juntar_janelas([(0.0, 2.8), (22.0, 24.0)]) == [(0.0, 2.8), (22.0, 24.0)]


def test_janela_quase_colada_tambem_funde():
    """Meio segundo de intervalo le como falha de montagem, nao como intencao."""
    assert LAY.juntar_janelas([(5.0, 6.0), (6.4, 7.0)]) == [(5.0, 7.0)]


def test_janelas_fora_de_ordem_sao_ordenadas():
    assert LAY.juntar_janelas([(22.0, 24.0), (0.0, 2.8)]) == [(0.0, 2.8), (22.0, 24.0)]


def test_sem_janela_nao_quebra():
    assert LAY.juntar_janelas([]) == []


def test_resumo_gancho_e_cta_pedem_a_tela_inteira():
    assert set(LAY.SOZINHOS) == {"resumo", "gancho", "cta"}

"""Estúdio HyperFrames do @previsaorj: cenas, cinco regiões e marca certa."""
import json
from pathlib import Path
import sys

import pytest

pytest.importorskip('numpy')  # o CI enxuto não instala as dependências de render

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'hyperframes'))

from compor import compor  # noqa: E402
from gerar_hf import agrupar_cenas, ceu_do_dia, tempos_das_palavras  # noqa: E402
from src.previsao_rj.editorial.formats import amanha_no_rio, rio_antes_de_sair  # noqa: E402

SNAP = json.loads((ROOT / 'tests/fixtures/snapshot_rj.json').read_text(encoding='utf-8'))


def pacote(personagem='bira', fn=rio_antes_de_sair, formato='rio_antes_de_sair'):
    from src.previsao_rj.editorial.cinco import cinco_regioes
    batidas = fn(SNAP, False)
    t, tempos = 0.0, []
    for b in batidas:
        tempos.append((t, t + 2.5))
        t += 2.8
    cenas = agrupar_cenas(batidas)
    for c in cenas:
        c['ini'] = tempos[c['batidas'][0]][0]
    palavras = []
    for i, b in enumerate(batidas):
        for w in tempos_das_palavras(b['legenda'], *tempos[i]):
            w['b'] = i
            palavras.append(w)
    locs = SNAP['forecast']['today']['locations']
    return {'dur': round(t + 0.9, 2), 'personagem': personagem, 'formato': formato, 'demo': True,
            'data': '2026-10-01', 'data_ext': 'QUINTA, 1 DE OUTUBRO', 'data_previsao': '2026-10-01',
            'hora': '06:00', 'ceu': ceu_do_dia(locs), 'cidades': cinco_regioes(locs),
            'batidas': [dict(b, ini=tempos[i][0], fim=tempos[i][1]) for i, b in enumerate(batidas)],
            'cenas': cenas, 'cortes': [c['ini'] - 0.25 for c in cenas[1:]],
            'transicoes': ['whip-pan'] * (len(cenas) - 1), 'palavras': palavras,
            'boca': [[0.0, 'X'], [0.5, 'D']]}


def test_cenas_seguem_o_roteiro():
    batidas = rio_antes_de_sair(SNAP, False)
    tipos = [c['tipo'] for c in agrupar_cenas(batidas)]
    assert tipos[0] == 'abertura'
    assert tipos[-1] == 'cta'
    assert 'quadro' in tipos
    assert sum(len(c['batidas']) for c in agrupar_cenas(batidas)) == len(batidas)


def test_formato_sem_cta_fecha_com_card_de_seguir():
    batidas = [{'tipo': 'nenhum', 'legenda': 'a', 'fala': 'a', 'dados': {}},
               {'tipo': 'resumo', 'legenda': 'b', 'fala': 'b', 'dados': {}},
               {'tipo': 'nenhum', 'legenda': 'Previsão RJ.', 'fala': 'c', 'dados': {}}]
    assert [c['tipo'] for c in agrupar_cenas(batidas)] == ['abertura', 'quadro', 'cta']


def test_html_tem_cinco_previsoes_e_marca_do_rio():
    html = compor(pacote())
    for c in pacote()['cidades']:
        assert c['nome'].upper() in html
    assert '@PREVISAORJ' in html and 'BIRA DO TEMPO' in html
    assert 'Math.random' not in html and 'Date.now' not in html
    assert 'window.__timelines["main"]' in html


def test_bia_amanha():
    # A fixture técnica não tem o bloco de amanhã: usa o de hoje no lugar dele.
    snap = dict(SNAP, forecast=dict(SNAP['forecast'], tomorrow=SNAP['forecast']['today']))
    html = compor(pacote('bia', lambda s, i: amanha_no_rio(snap, i), 'amanha_no_rio'))
    assert 'BIA DA ORLA' in html and 'AMANHÃ NO RIO' in html


def test_card_de_seguir_e_da_conta_do_rio():
    card = (ROOT / 'hyperframes/compositions/instagram-follow.html').read_text(encoding='utf-8')
    assert '@previsaorj' in card


def test_palavras_dentro_da_fala():
    ws = tempos_das_palavras('Amanhã, o tempo no Rio fica assim.', 1.0, 3.0)
    assert ws[0]['s'] == 1.0 and ws[-1]['e'] <= 3.0 + 1e-6

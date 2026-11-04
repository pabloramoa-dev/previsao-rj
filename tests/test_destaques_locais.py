"""Rotação editorial hiperlocal sem retirar as seis regiões obrigatórias."""
from __future__ import annotations

from copy import deepcopy

import pytest

from src.previsao_rj.editorial.duracao import cortar_para_janela
from src.previsao_rj.editorial.formats import (
    amanha_no_rio, destaque_da_semana, gancho_destaque, rio_antes_de_sair,
)

SG = {'id': 'sao_goncalo', 'name': 'São Gonçalo',
      'municipality': 'sao_goncalo', 'zone': 'leste_metropolitano',
      'min_c': 22, 'max_c': 31, 'rain_probability_pct': 35,
      'wind_gust_max_kmh': 20}


def com_data_e_goncalo(snapshot, data):
    doc = deepcopy(snapshot)
    doc['forecast']['today']['date'] = data
    for turno in ('today', 'tomorrow'):
        doc['forecast'][turno]['locations'].append(dict(SG))
    return doc


@pytest.mark.parametrize(('data', 'esperado'), [
    ('2026-11-02', 'sao_goncalo'),  # segunda
    ('2026-11-03', 'icarai'),       # terça
    ('2026-11-04', None),           # quarta: pauta normal
    ('2026-11-05', 'sao_goncalo'),  # quinta: reforço semanal
    ('2026-11-06', None),           # sexta: pauta normal
    ('2026-11-07', 'icarai'),       # sábado
    ('2026-11-08', None),           # domingo: pauta normal
])
def test_rodizio_pelo_dia_de_publicacao(snapshot, data, esperado):
    doc = com_data_e_goncalo(snapshot, data)
    locais = doc['forecast']['today']['locations']
    escolhido = destaque_da_semana(doc, locais)
    assert (escolhido['id'] if escolhido else None) == esperado


@pytest.mark.parametrize('data', ['2026-11-02', '2026-11-05'])
def test_sao_goncalo_falado_de_manha_e_noite(snapshot, data):
    doc = com_data_e_goncalo(snapshot, data)
    for montar, previsto in ((rio_antes_de_sair, 'Hoje'), (amanha_no_rio, 'Em')):
        beats = montar(doc, incerto=False)
        destaque = [b for b in beats if b['dados'].get('destaque_local')]
        assert len(destaque) == 1
        assert 'São Gonçalo' in destaque[0]['fala']
        assert 'mínima de 22' in destaque[0]['fala']
        assert 'máxima de 31' in destaque[0]['fala']
        assert destaque[0]['fala'].startswith(previsto)
        assert len([b for b in beats if b['tipo'] == 'resumo']) == 1
        assert len(next(b for b in beats if b['tipo'] == 'resumo')['dados']['cidades']) == 6


@pytest.mark.parametrize('data', ['2026-11-03', '2026-11-07'])
def test_icarai_e_identificado_como_bairro_de_niteroi(snapshot, data):
    doc = com_data_e_goncalo(snapshot, data)
    for montar in (rio_antes_de_sair, amanha_no_rio):
        beats = montar(doc, incerto=False)
        destaque = next(b for b in beats if b['dados'].get('destaque_local'))
        assert 'Icaraí, Niterói' in destaque['fala']
        assert 'máxima de ' in destaque['fala']


def test_nao_cita_sao_goncalo_sem_previsao_valida(snapshot):
    doc = com_data_e_goncalo(snapshot, '2026-11-02')
    locais = doc['forecast']['today']['locations']
    next(l for l in locais if l['id'] == 'sao_goncalo')['max_c'] = None
    assert destaque_da_semana(doc, locais) is None
    assert gancho_destaque(doc, locais, 'hoje') is None


def test_editor_de_duracao_preserva_destaque_programado():
    def beat(tipo, *, destaque=False):
        return {'fala': tipo, 'tipo': tipo, 'dados': {'destaque_local': destaque}}
    batidas = [beat('nenhum'), beat('gancho', destaque=True),
               beat('resumo'), beat('gancho'), beat('cta')]
    finais, cortados = cortar_para_janela(batidas, [5, 9, 10, 14, 5])
    assert 1 not in cortados
    assert any(b['dados'].get('destaque_local') for b in finais)

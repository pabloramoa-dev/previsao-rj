"""Dois Reels por dia (decisão de 16/09/2026):

- 6h: Bira do Tempo, previsão do DIA (`reel_manha.yml`);
- 18h: Bia da Orla, previsão de AMANHÃ (`reel_noite.yml`, formato `amanha_no_rio`).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.previsao_rj.editorial.engine import evaluate
from src.previsao_rj.editorial.formats import prepare
from src.previsao_rj.editorial.turnos import apresentador, do_turno, turno_do_formato
from src.previsao_rj.publish import state
from src.previsao_rj.publish.caption import build_caption

FUTURO = '2099-01-01T00:00:00-03:00'
MANHA = Path('.github/workflows/reel_manha.yml')
NOITE = Path('.github/workflows/reel_noite.yml')
CINCO = ['Niterói', 'Centro do Rio', 'Zona Sul', 'Baixada', 'Campo Grande']


def test_apresentador_segue_o_turno():
    assert turno_do_formato('amanha_no_rio') == 'noite'
    assert apresentador('amanha_no_rio') == 'bia'
    for formato in ('rio_antes_de_sair', 'chove_onde', 'vai_dar_praia', 'fim_de_semana'):
        assert turno_do_formato(formato) == 'manha'
        assert apresentador(formato) == 'bira'
    with pytest.raises(ValueError):
        do_turno({'format': 'x'}, 'madrugada')


def test_motor_gera_pauta_de_amanha_com_a_bia(snapshot):
    pautas = evaluate(snapshot)
    amanha = [c for c in pautas if c['format'] == 'amanha_no_rio']
    assert len(amanha) == 1
    assert amanha[0]['character'] == 'bia' and amanha[0]['turno'] == 'noite'
    assert amanha[0]['extra']['date'] == snapshot['forecast']['tomorrow']['date']
    assert all(c['character'] == 'bira' for c in pautas if c['format'] != 'amanha_no_rio')


def test_sem_alternancia_por_historico(snapshot):
    """Antes, dois Reels seguidos do mesmo apresentador trocavam o terceiro.
    Agora o turno manda: manhã é sempre Bira, noite é sempre Bia."""
    historico = [{'status': 'published', 'published_at': snapshot['generated_at'],
                  'character': 'bira', 'format': 'rio_antes_de_sair', 'topic': 'x'}] * 2
    for c in evaluate(snapshot, historico):
        assert c['character'] == apresentador(c['format'])


def test_roteiro_de_amanha_le_o_bloco_de_amanha(snapshot):
    amanha = snapshot['forecast']['tomorrow']['locations']
    for loc in amanha:
        loc['max_c'] = 40.0
    beats = prepare(snapshot, 'amanha_no_rio')['beats']
    assert beats[0]['tipo'] == 'nenhum' and 'Amanhã' in beats[0]['fala']
    assert beats[-1]['tipo'] == 'cta'
    resumo = [b for b in beats if b['tipo'] == 'resumo']
    assert len(resumo) == 1
    assert resumo[0]['dados']['titulo'] == 'AMANHÃ NA REGIÃO'
    assert [c['nome'] for c in resumo[0]['dados']['cidades']] == CINCO
    assert all(c['max'] == 40.0 for c in resumo[0]['dados']['cidades'])
    assert resumo[0]['fala'].startswith('Niterói, Centro, Zona Sul, Baixada e Campo Grande')
    falas = ' '.join(b['fala'] for b in beats)
    assert falas.count('Amanhã') + falas.count('amanhã') <= 3   # sem repetição cansativa
    ganchos = [b for b in beats if b['tipo'] == 'gancho']
    assert ganchos and all('AMANHÃ' in b['dados']['sub'] for b in ganchos)
    palavras = sum(len(b['fala'].split()) for b in beats)
    assert 20 <= palavras <= 80, palavras


def test_legenda_de_amanha_nao_usa_dado_de_hoje(snapshot):
    for loc in snapshot['forecast']['tomorrow']['locations']:
        loc['max_c'] = 41.0
    item = {'format': 'amanha_no_rio', 'topic': 'amanha', 'location_ids': [], 'facts': {}}
    legenda = build_caption(snapshot, item)
    assert legenda.startswith('Amanhã')
    assert '41°' in legenda
    for nome in CINCO:
        assert f'📍 {nome}:' in legenda
    assert '@previsaorj' in legenda
    snapshot['forecast']['tomorrow']['locations'] = []
    with pytest.raises(ValueError):
        build_caption(snapshot, item)


def _fila(tmp_path, *itens):
    caminho = tmp_path / 'fila.json'
    caminho.write_text(json.dumps(list(itens)), encoding='utf-8')
    return caminho


def _item(chave, formato, total, **extra):
    base = {'dedupe_key': chave, 'format': formato, 'status': 'ready',
            'expires_at': FUTURO, 'total': total}
    base.update(extra)
    return base


def test_fila_separa_os_turnos(tmp_path):
    fila = _fila(tmp_path, _item('hoje', 'rio_antes_de_sair', 15),
                 _item('amanha', 'amanha_no_rio', 20))
    assert state.next_ready(fila, turno='manha')['dedupe_key'] == 'hoje'
    assert state.next_ready(fila, turno='noite')['dedupe_key'] == 'amanha'
    assert state.next_ready(fila)['dedupe_key'] == 'amanha'


def test_trava_de_um_turno_nao_segura_o_outro(tmp_path):
    fila = _fila(tmp_path, _item('m', 'rio_antes_de_sair', 15, status='published',
                                 published_at='2026-09-17T05:02:00-03:00', media_id='1'))
    assert state.published_on(fila, '2026-09-17', turno='manha')['media_id'] == '1'
    assert state.published_on(fila, '2026-09-17', turno='noite') is None
    assert state.published_on(fila, '2026-09-17') is not None


def carregar(caminho):
    return yaml.safe_load(caminho.read_text(encoding='utf-8'))


def test_workflow_da_noite_tem_travas_e_horario_da_tarde():
    noite = carregar(NOITE)
    assert noite['jobs']['trava']['if'] == "vars.AUTOMATION_ENABLED == 'true'"
    assert noite['jobs']['reel']['if'] == "needs.trava.outputs.pular != 'sim'"
    assert noite['concurrency'] == carregar(MANHA)['concurrency']
    horas = {int(c['cron'].split()[1]) for c in noite[True]['schedule']}
    # 16h30-17h30 de Brasília (UTC-3): antes das 18h, depois do meio-dia.
    assert len(noite[True]['schedule']) >= 2 and min(horas) >= 18 and max(horas) < 21
    texto = NOITE.read_text(encoding='utf-8')
    assert '--turno noite' in texto and '--exigir-inedito-hoje' in texto
    assert "i.get('format') == 'amanha_no_rio'" in texto


def test_workflow_da_manha_escolhe_so_pauta_do_dia():
    texto = MANHA.read_text(encoding='utf-8')
    assert '--turno manha' in texto
    assert "i.get('format') != 'amanha_no_rio'" in texto

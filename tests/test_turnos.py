"""Dois Reels por dia (decisão de 16/09/2026):

- 6h: Bira do Tempo, previsão do DIA (`reel_manha.yml`);
- 18h: Bia da Orla, previsão de AMANHÃ (`reel_noite.yml`, formato `amanha_no_rio`).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
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
    # Reservas entre 12h e 15h de Brasília (UTC-3): depois do meio-dia e com
    # folga de horas antes do preparo das 17:20.
    assert len(noite[True]['schedule']) >= 2 and min(horas) >= 15 and max(horas) <= 18
    assert noite['env']['ALVO'] == '18:00'
    assert noite[True]['repository_dispatch']['types'] == ['reel_noite']
    texto = NOITE.read_text(encoding='utf-8')
    assert '--turno noite' in texto and '--exigir-inedito-hoje' in texto
    assert "i.get('format') == 'amanha_no_rio'" in texto


def test_workflow_da_manha_escolhe_so_pauta_do_dia():
    texto = MANHA.read_text(encoding='utf-8')
    assert '--turno manha' in texto
    assert "i.get('format') != 'amanha_no_rio'" in texto


# --- 17/09/2026: preparar antes, publicar na hora -------------------------

def test_manha_nao_publica_fim_de_semana(tmp_path):
    """Numa quinta, a manhã escolheu `fim_de_semana` (maior nota). Manhã é
    previsão de HOJE."""
    fila = _fila(tmp_path, _item('fds', 'fim_de_semana', 30),
                 _item('hoje', 'rio_antes_de_sair', 12),
                 _item('amanha', 'amanha_no_rio', 40))
    assert state.next_ready(fila, turno='manha')['dedupe_key'] == 'hoje'
    assert state.next_ready(fila, turno='noite')['dedupe_key'] == 'amanha'
    so_fds = _fila(tmp_path, _item('fds', 'fim_de_semana', 30))
    assert state.next_ready(so_fds, turno='manha') is None
    assert state.next_ready(so_fds, turno='noite') is None


def test_base_diaria_nao_e_vetada_por_numeros_de_outro_dia(snapshot):
    """Máximas, chuva e vento iguais aos de ontem não podem tirar o Reel do ar."""
    hoje = snapshot['forecast']['today']['date']
    for formato in ('rio_antes_de_sair', 'amanha_no_rio'):
        base = next(c for c in evaluate(snapshot) if c['format'] == formato)
        # Mesmos fatos e mesmo gancho; a chave de ontem tem a data de ontem.
        gerado = datetime.fromisoformat(snapshot['generated_at'])
        ontem = dict(base, status='published', dedupe_key='chave-de-ontem',
                     published_at=(gerado - timedelta(days=1)).isoformat())
        repetido = next(c for c in evaluate(snapshot, [ontem], reference=gerado)
                        if c['format'] == formato)
        assert repetido['status'] == 'ready', (formato, repetido['vetoes'])
        # No MESMO dia, continua vetado.
        ontem['published_at'] = gerado.replace(hour=0, minute=1).isoformat()
        if ontem['published_at'][:10] == hoje:
            mesmo = next(c for c in evaluate(snapshot, [ontem], reference=gerado)
                         if c['format'] == formato)
            assert 'duplicata' in mesmo['vetoes'] or 'sem_mudanca_material' in mesmo['vetoes']


def test_render_desenha_o_topico_da_pauta(snapshot):
    pautas = [c for c in evaluate(snapshot) if c['format'] == 'chove_onde' and c['status'] == 'ready']
    for pauta in pautas:
        assert prepare(snapshot, 'chove_onde', topic=pauta['topic'])['candidate']['topic'] == pauta['topic']
    with pytest.raises(ValueError):
        prepare(snapshot, 'chove_onde', topic='topico_inexistente')


def test_hora_do_roteiro_e_a_hora_de_ir_ao_ar(monkeypatch):
    from src.previsao_rj.editorial import script
    monkeypatch.setenv('PREVISAO_RJ_HORA_ALVO', '6')
    assert script.hora_agora() >= 6
    monkeypatch.setenv('PREVISAO_RJ_HORA_ALVO', '23')
    assert script.hora_agora() == 23


def test_relogio_do_turno():
    from scripts.aguardar_horario import BRT, dentro_do_prazo, segundos_de_espera
    cedo = datetime(2026, 9, 18, 0, 47, tzinfo=BRT)
    assert segundos_de_espera('06:00', 40, cedo) == ((5 * 60 + 20) - 47) * 60
    assert segundos_de_espera('06:00', 0, datetime(2026, 9, 18, 5, 26, tzinfo=BRT)) == 34 * 60
    assert segundos_de_espera('06:00', 40, datetime(2026, 9, 18, 9, 45, tzinfo=BRT)) == 0
    assert dentro_do_prazo('10:00', datetime(2026, 9, 18, 9, 59, tzinfo=BRT))
    assert not dentro_do_prazo('10:00', datetime(2026, 9, 18, 10, 1, tzinfo=BRT))


@pytest.mark.parametrize('caminho,alvo', [(MANHA, '06:00'), (NOITE, '18:00')])
def test_workflow_prepara_antes_e_publica_na_hora(caminho, alvo):
    wf = carregar(caminho)
    assert wf['env']['ALVO'] == alvo and int(wf['env']['PREPARO_MIN']) >= 20
    passos = [s.get('name') or s.get('uses') for s in wf['jobs']['reel']['steps']]
    preparo = passos.index('Aguardar a hora de preparar (ALVO - PREPARO_MIN)')
    publicar = passos.index('Aguardar o horário de publicar (ALVO)')
    assert preparo < passos.index('Coletar a previsão atual')
    assert passos.index('Render com a pauta escolhida') < publicar
    assert passos.index('QA') < publicar < passos.index('Publicar o Reel do dia')
    assert publicar < passos.index('Hospedar MP4 em Release temporário')
    assert wf['jobs']['reel']['timeout-minutes'] <= 355
    assert wf['jobs']['reel']['env']['PREVISAO_RJ_HORA_ALVO'] == str(int(alvo[:2]))
    texto = caminho.read_text(encoding='utf-8')
    assert '--topico "${{ steps.pauta.outputs.topico }}"' in texto
    assert "os.environ['PRAZO']" in texto
    for passo in wf['jobs']['trava']['steps'] + wf['jobs']['reel']['steps']:
        if passo.get('uses', '').startswith('actions/checkout'):
            assert passo['with']['ref'] == '${{ github.ref_name }}'

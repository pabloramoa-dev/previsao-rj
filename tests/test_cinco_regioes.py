"""Todo Reel mostra pelo menos cinco previsões: Niterói, Centro do Rio,
Zona Sul, Baixada e Campo Grande (decisão de 16/09/2026)."""
import copy

import pytest

from src.previsao_rj.editorial.cinco import cinco_regioes, fala_resumo, faltando
from src.previsao_rj.editorial.formats import prepare
from src.previsao_rj.editorial.duracao import cortar_para_janela

OBRIGATORIAS = ['Niterói', 'Centro do Rio', 'Zona Sul', 'Baixada', 'Campo Grande']

# Os oito pontos-âncora (sample_tier 1) que a coleta diária traz.
TIER1 = [
    ('copacabana', 'Copacabana', 'zona_sul', 22, 29),
    ('tijuca', 'Tijuca', 'grande_tijuca', 21, 31),
    ('centro_rio', 'Centro', 'centro', 22, 32),
    ('barra_da_tijuca', 'Barra da Tijuca', 'barra_recreio', 21, 30),
    ('campo_grande', 'Campo Grande', 'zona_oeste', 20, 34),
    ('icarai', 'Icaraí', 'niteroi_baia', 22, 28),
    ('duque_de_caxias', 'Duque de Caxias', 'baixada', 22, 35),
    ('nova_iguacu', 'Nova Iguaçu', 'baixada', 21, 35),
]


def locais():
    return [{'id': i, 'name': n, 'zone': z, 'min_c': lo, 'max_c': hi,
             'rain_probability_pct': 20, 'gust_kmh': 20}
            for i, n, z, lo, hi in TIER1]


def test_coleta_diaria_vira_as_cinco_na_ordem():
    linhas = cinco_regioes(locais())
    assert [l['nome'] for l in linhas] == OBRIGATORIAS
    assert [l['id'] for l in linhas] == ['icarai', 'centro_rio', 'copacabana',
                                         'duque_de_caxias', 'campo_grande']
    assert faltando(linhas) == []


def test_ponto_preferido_ausente_usa_outro_da_mesma_zona():
    locs = [l for l in locais() if l['id'] != 'duque_de_caxias']
    baixada = [l for l in cinco_regioes(locs) if l['nome'] == 'Baixada'][0]
    assert baixada['id'] == 'nova_iguacu'


def test_zona_sem_id_conhecido_ainda_conta():
    locs = [l for l in locais() if l['id'] != 'icarai']
    locs.append({'id': 'ponto_novo', 'name': 'Piratininga', 'zone': 'niteroi_oceanica',
                 'min_c': 21, 'max_c': 27})
    niteroi = [l for l in cinco_regioes(locs) if l['nome'] == 'Niterói'][0]
    assert niteroi['id'] == 'ponto_novo'


def test_regiao_ausente_nao_empresta_numero_e_completa_com_nome_real():
    locs = [l for l in locais() if l['id'] != 'campo_grande']
    linhas = cinco_regioes(locs)
    assert len(linhas) == 5
    assert 'Campo Grande' not in [l['nome'] for l in linhas]
    assert faltando(linhas) == ['Campo Grande']
    extra = linhas[-1]
    assert extra['regiao'] is None and extra['nome'] in {'Tijuca', 'Barra da Tijuca', 'Nova Iguaçu'}


def test_ponto_sem_minima_ou_maxima_fica_de_fora():
    locs = locais()
    for l in locs:
        if l['id'] == 'centro_rio':
            l.pop('min_c')
    linhas = cinco_regioes(locs)
    assert 'Centro do Rio' not in [l['nome'] for l in linhas]
    assert all(isinstance(l['min'], (int, float)) for l in linhas)


def test_fala_do_resumo_e_curta_e_nomeia_as_regioes():
    fala = fala_resumo(cinco_regioes(locais()))
    assert fala == 'Niterói, Centro, Zona Sul, Baixada e Campo Grande: de 28 a 35 graus.'
    assert len(fala.split()) <= 13
    assert fala_resumo(cinco_regioes(locais()), 'No sábado').startswith('No sábado, em Niterói')


@pytest.fixture
def snap_tier1(snapshot):
    s = copy.deepcopy(snapshot)
    s['forecast']['today']['locations'] = locais()
    return s


def test_formato_principal_mostra_as_cinco(snap_tier1):
    beats = prepare(snap_tier1, 'rio_antes_de_sair')['beats']
    resumo = [b for b in beats if b['tipo'] == 'resumo']
    assert len(resumo) == 1
    assert [c['nome'] for c in resumo[0]['dados']['cidades']] == OBRIGATORIAS
    palavras = sum(len(b['fala'].split()) for b in beats)
    assert palavras <= 80


def test_corte_por_duracao_nunca_tira_as_cinco(snap_tier1):
    beats = prepare(snap_tier1, 'rio_antes_de_sair')['beats']
    duracoes = [9.0] * len(beats)          # dia longo: tudo estoura o teto
    ficam, _ = cortar_para_janela(beats, duracoes)
    assert any(b['tipo'] == 'resumo' for b in ficam)


def test_fim_de_semana_mostra_as_cinco_em_cada_dia(snap_tier1, monkeypatch):
    import src.previsao_rj.editorial.formats as F
    locs = snap_tier1['forecast']['today']['locations']
    snap_tier1['forecast']['saturday'] = {'date': '2026-09-19', 'locations': copy.deepcopy(locs)}
    snap_tier1['forecast']['sunday'] = {'date': '2026-09-20', 'locations': copy.deepcopy(locs)}
    candidato = {'format': 'fim_de_semana', 'status': 'ready', 'topic': 'fim_de_semana',
                 'location_ids': [l['id'] for l in locs], 'language': 'deterministic',
                 'extra': {'dates': ['2026-09-19', '2026-09-20']},
                 'created_at': '2026-09-17T06:00:00-03:00'}
    monkeypatch.setattr(F, 'evaluate', lambda *a, **k: [candidato])
    beats = F.prepare(snap_tier1, 'fim_de_semana')['beats']
    resumos = [b for b in beats if b['tipo'] == 'resumo']
    assert [r['dados']['titulo'] for r in resumos] == ['SÁBADO NA REGIÃO', 'DOMINGO NA REGIÃO']
    assert all([c['nome'] for c in r['dados']['cidades']] == OBRIGATORIAS for r in resumos)
    assert beats[0]['tipo'] == 'nenhum'
    assert not any('nos pontos consultados' in b['fala'] for b in beats)


def test_formato_de_chuva_tambem_mostra_as_cinco(snap_tier1):
    try:
        beats = prepare(snap_tier1, 'chove_onde')['beats']
    except ValueError:
        pytest.skip('fixture sem pauta de chuva pronta')
    resumo = [b for b in beats if b['tipo'] == 'resumo']
    assert len(resumo) == 1
    assert [c['nome'] for c in resumo[0]['dados']['cidades']] == OBRIGATORIAS
    assert beats[-1]['tipo'] != 'resumo'

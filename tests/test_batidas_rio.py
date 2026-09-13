"""O formato principal precisa virar cartao na tela, nao so locucao.

A execucao #1 do publicar_manual saiu com 2 batidas de tipo 'nenhum' e 20,9s:
audio correto, tela vazia. Estes testes prendem o contrato que faltava — cada
batida tipada carrega os campos que o painel correspondente le, e nenhuma
batida aparece sem o dado que ela mostra.
"""
import pytest

from src.previsao_rj.editorial.formats import prepare

# O que scene.painel() le de cada tipo. Se o painel mudar, isto quebra aqui e
# nao no render dentro do workflow.
CAMPOS = {'gancho': ('numero',), 'resumo': ('cidades',), 'alerta': ('titulo',),
          'cta': (), 'nenhum': ()}


def batidas(snapshot):
    return prepare(snapshot, 'rio_antes_de_sair')['beats']


def test_batidas_tem_cartao_e_nao_so_locucao(snapshot):
    tipos = [b['tipo'] for b in batidas(snapshot)]
    assert tipos.count('nenhum') < len(tipos), 'Reel inteiro sem cartao'
    assert 'resumo' in tipos and 'cta' in tipos and 'gancho' in tipos


def test_cada_batida_carrega_o_que_o_painel_le(snapshot):
    for b in batidas(snapshot):
        assert b['tipo'] in CAMPOS, f"tipo {b['tipo']} sem painel conhecido"
        faltando = [c for c in CAMPOS[b['tipo']] if c not in b['dados']]
        assert not faltando, f"{b['tipo']} sem {faltando}"
        assert b['fala'].strip() and b['legenda'] == b['fala']


def test_resumo_so_lista_cidade_com_minima_e_maxima(snapshot):
    locs = snapshot['forecast']['today']['locations']
    locs[0].pop('min_c')
    resumo = [b for b in batidas(snapshot) if b['tipo'] == 'resumo'][0]
    nomes = [c['nome'] for c in resumo['dados']['cidades']]
    assert locs[0]['name'] not in nomes
    assert all(isinstance(c['min'], (int, float)) for c in resumo['dados']['cidades'])


def test_sem_probabilidade_nao_inventa_cartao_de_chuva(snapshot):
    for loc in snapshot['forecast']['today']['locations']:
        loc.pop('rain_probability_pct', None)
    saida = batidas(snapshot)
    assert not any('CHANCE DE CHUVA' == b['dados'].get('sub') for b in saida)
    assert any('não está disponível' in b['fala'] for b in saida)


def test_vento_fraco_nao_gera_alerta(snapshot):
    for loc in snapshot['forecast']['today']['locations']:
        loc['wind_gust_max_kmh'] = 12
        loc['gust_kmh'] = 12
    assert not any(b['tipo'] == 'alerta' for b in batidas(snapshot))


def test_abre_sem_cartao_para_o_apresentador_existir(snapshot):
    """Gancho, resumo e CTA tiram o apresentador de cena (LAY.SOZINHOS).

    Se toda batida fosse dessas, o Reel inteiro seria locucao sobre cenario
    vazio — que foi o defeito visto no primeiro render com dado real.
    """
    saida = batidas(snapshot)
    assert saida[0]['tipo'] == 'nenhum' and not saida[0]['dados']
    from src.previsao_rj.render.characters import layout as LAY
    assert any(b['tipo'] not in LAY.SOZINHOS for b in saida)


def test_incerteza_vem_antes_de_qualquer_numero(snapshot):
    snapshot['confidence'] = {'score': 40, 'band': 'baixa'}
    saida = batidas(snapshot)
    avisos = [i for i, b in enumerate(saida) if 'incerteza' in b['fala']]
    numeros = [i for i, b in enumerate(saida) if b['tipo'] == 'gancho']
    if avisos:
        assert avisos[0] < numeros[0]


def test_roteiro_cabe_no_portao_de_qa(snapshot):
    """QA corta fora de 12-40s. A ~2,5 palavras/s, 80 palavras ja e o teto."""
    palavras = sum(len(b['fala'].split()) for b in batidas(snapshot))
    assert 20 <= palavras <= 80, f'{palavras} palavras'


def test_temperatura_uniforme_nao_vira_gancho_de_contraste(snapshot):
    for loc in snapshot['forecast']['today']['locations']:
        loc['max_c'] = 25
    gancho = [b for b in batidas(snapshot) if b['tipo'] == 'gancho'][0]
    assert gancho['dados']['sub'] == 'MÁXIMA PREVISTA HOJE'
    assert 'muda pela região' not in gancho['fala']

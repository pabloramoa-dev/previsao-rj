"""O Reel cabe na janela editorial, e o que sai do ar sai por critério.

Caso que originou o módulo: execução 34964321124 (15/09/2026), primeiro fluxo
diário com dado ao vivo. Oito batidas, 43,2 s de narração, QA recusou no teto de
40 s e o Reel não foi publicado.
"""
from __future__ import annotations

import pytest

from src.previsao_rj.editorial.duracao import PISO, TETO, cortar_para_janela


def b(tipo, fala='fala'):
    return {'fala': fala, 'legenda': fala, 'tipo': tipo, 'dados': {}}


# As oito batidas e as durações da execução que falhou.
CASO_REAL = [b('nenhum', 'abertura'), b('nenhum', 'incerteza'), b('gancho', 'contraste'),
             b('resumo', 'cidades'), b('gancho', 'chuva'), b('alerta', 'vento'),
             b('gancho', 'extra'), b('cta', 'cta')]
DURACOES_REAIS = [3.95, 7.72, 3.67, 7.72, 3.31, 7.72, 3.84, 3.50]  # soma 41.43


def test_roteiro_curto_nao_e_tocado():
    batidas = [b('nenhum'), b('gancho'), b('cta')]
    ficam, cortadas = cortar_para_janela(batidas, [5, 10, 5])
    assert cortadas == []
    assert ficam == batidas


def test_caso_real_passa_a_caber_no_teto():
    ficam, cortadas = cortar_para_janela(CASO_REAL, DURACOES_REAIS)
    restante = sum(d for i, d in enumerate(DURACOES_REAIS) if i not in cortadas)
    assert cortadas, 'o caso real precisa ser cortado'
    assert restante <= TETO
    assert len(ficam) == len(CASO_REAL) - len(cortadas)


def test_abertura_e_cta_nunca_saem():
    ficam, cortadas = cortar_para_janela(CASO_REAL, DURACOES_REAIS)
    assert 0 not in cortadas
    assert len(CASO_REAL) - 1 not in cortadas
    assert ficam[0]['fala'] == 'abertura'
    assert ficam[-1]['fala'] == 'cta'


def test_resumo_das_cinco_previsoes_nunca_sai():
    """Decisão de 16/09/2026: todo Reel mostra as cinco previsões (Niterói,
    Centro do Rio, Zona Sul, Baixada e Campo Grande). Quem cai é o gancho
    secundário; o alerta continua preservado."""
    _, cortadas = cortar_para_janela(CASO_REAL, DURACOES_REAIS)
    tipos = [CASO_REAL[i]['tipo'] for i in cortadas]
    assert 'resumo' not in tipos
    assert 'alerta' not in tipos
    assert 'gancho' in tipos


def test_resumo_protegido_mesmo_quando_e_a_batida_mais_longa():
    batidas = [b('nenhum'), b('resumo'), b('gancho'), b('nenhum'), b('cta')]
    duracoes = [8.0, 14.0, 6.0, 9.0, 6.0]  # 43 s
    ficam, cortadas = cortar_para_janela(batidas, duracoes)
    assert 1 not in cortadas
    assert any(x['tipo'] == 'resumo' for x in ficam)


def test_corte_para_quando_ja_coube():
    """Nada de encurtar além do necessário: cada batida a menos é informação a menos."""
    _, cortadas = cortar_para_janela(CASO_REAL, DURACOES_REAIS)
    # Devolver a última batida cortada estouraria de novo o teto.
    restante = sum(d for i, d in enumerate(DURACOES_REAIS) if i not in cortadas)
    maior_cortada = max(DURACOES_REAIS[i] for i in cortadas)
    assert restante + maior_cortada > TETO


def test_nao_cai_abaixo_do_piso_quando_da_para_evitar():
    # Cortar o gancho (20 s, o primeiro da fila) derrubaria o Reel para 22 s;
    # o corte pula ele e tira a incerteza (6 s).
    batidas = [b('nenhum'), b('gancho'), b('nenhum'), b('resumo'), b('cta')]
    duracoes = [5.0, 20.0, 6.0, 6.0, 5.0]  # 42 s
    ficam, cortadas = cortar_para_janela(batidas, duracoes)
    restante = sum(d for i, d in enumerate(duracoes) if i not in cortadas)
    assert restante <= TETO
    assert restante >= PISO
    assert cortadas == [2]
    assert len(ficam) == 4


def test_roteiro_impossivel_para_no_minimo_e_deixa_o_qa_recusar():
    """Quando nem cortando tudo cabe, o corte para no mínimo de três batidas e
    deixa o QA recusar. Reel de abertura + CTA, sem previsão nenhuma, seria pior
    do que não publicar: o seguidor abriria um vídeo que não diz o tempo."""
    batidas = [b('nenhum'), b('resumo'), b('gancho'), b('gancho'), b('cta')]
    duracoes = [18.0, 14.0, 14.0, 14.0, 18.0]  # 78 s, tudo grande
    ficam, cortadas = cortar_para_janela(batidas, duracoes)
    assert len(ficam) == 3
    assert len(cortadas) == 2
    restante = sum(d for i, d in enumerate(duracoes) if i not in cortadas)
    assert restante > TETO  # e o gate de `qa_video.py` é quem barra


def test_nunca_sobra_menos_de_tres_batidas():
    batidas = [b('nenhum'), b('resumo'), b('resumo'), b('resumo'), b('cta')]
    duracoes = [20.0, 20.0, 20.0, 20.0, 20.0]
    ficam, _ = cortar_para_janela(batidas, duracoes)
    assert len(ficam) >= 3


def test_uma_duracao_por_batida():
    with pytest.raises(ValueError):
        cortar_para_janela([b('nenhum'), b('cta')], [1.0])


# --------------------------------------------- janela de chuva e o relógio

from src.previsao_rj.editorial.script import janela_legivel  # noqa: E402


DIA_TODO = {'start': '00:00', 'end': '23:00',
            'peak_hour': '01:00', 'peak_probability_pct': 78}


def test_pico_que_ja_passou_nao_e_anunciado():
    """O Reel sai às 6h. "Pico por volta das 01:00" é chuva de ontem à noite
    contada para quem está decidindo se leva guarda-chuva hoje."""
    assert janela_legivel(DIA_TODO, agora=6) is None


def test_pico_ainda_a_frente_continua_valendo():
    adiante = {'start': '00:00', 'end': '23:00',
               'peak_hour': '19:00', 'peak_probability_pct': 90}
    leitura = janela_legivel(adiante, agora=6)
    assert leitura == {'tipo': 'pico', 'hora': '19:00', 'probabilidade': 90}


def test_janela_que_ja_terminou_some():
    passada = {'start': '00:00', 'end': '05:00',
               'peak_hour': '03:00', 'peak_probability_pct': 80}
    assert janela_legivel(passada, agora=6) is None


def test_janela_em_curso_e_cortada_no_agora():
    """Quem lê às 14h não precisa saber que começou às 9h."""
    leitura = janela_legivel({'start': '09:00', 'end': '18:00',
                              'peak_hour': '11:00',
                              'peak_probability_pct': 80}, agora=14)
    assert leitura == {'tipo': 'faixa', 'inicio': '14:00', 'fim': '18:00'}


def test_sem_relogio_o_comportamento_antigo_vale():
    assert janela_legivel(DIA_TODO) == {'tipo': 'pico', 'hora': '01:00',
                                        'probabilidade': 78}

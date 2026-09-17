"""Dois Reels por dia, cada um com o seu apresentador (decisão de 16/09/2026).

- MANHÃ (6h): Bira do Tempo apresenta a previsão DO DIA.
- NOITE (18h): Bia da Orla apresenta a previsão de AMANHÃ.

O turno é derivado do formato da pauta, não do relógio: é isso que deixa a
trava de "já publicado hoje" separar o Reel da manhã do Reel da noite, e que
impede o workflow da manhã de escolher a pauta de amanhã (e vice-versa).
Sem dependências, para ser usado pelo motor, pela fila e pelos workflows.
"""
from __future__ import annotations

TURNOS = ('manha', 'noite')

# Formatos que falam do dia SEGUINTE e, por isso, saem no turno da noite.
FORMATOS_NOITE = frozenset({'amanha_no_rio'})

# O que o Reel da MANHÃ pode publicar: só pauta sobre o DIA DE HOJE. Em
# 17/09/2026 (quinta) a manhã escolheu `fim_de_semana` porque era a pauta de
# maior nota — e o combinado é Bira com a previsão do dia. `fim_de_semana`
# continua sendo avaliado pelo motor, mas nenhum dos dois turnos o publica.
FORMATOS_MANHA = frozenset({'rio_antes_de_sair', 'chove_onde', 'vai_dar_praia',
                            'vai_ao_jogo'})

PUBLICAVEIS = {'manha': FORMATOS_MANHA, 'noite': FORMATOS_NOITE}

APRESENTADOR = {'manha': 'bira', 'noite': 'bia'}


def turno_do_formato(formato: str | None) -> str:
    return 'noite' if formato in FORMATOS_NOITE else 'manha'


def apresentador(formato: str | None) -> str:
    return APRESENTADOR[turno_do_formato(formato)]


def do_turno(item: dict, turno: str | None) -> bool:
    """True se o item da fila pertence ao turno (None = qualquer turno)."""
    if turno is None:
        return True
    if turno not in TURNOS:
        raise ValueError(f'turno desconhecido: {turno!r}')
    return turno_do_formato(item.get('format')) == turno


def publicavel_no_turno(item: dict, turno: str | None) -> bool:
    """True se o Reel diário daquele turno pode publicar o item.

    Diferente de `do_turno`, que diz a QUAL turno uma publicação pertence (é o
    que a trava de "já publicado hoje" usa): aqui é a lista fechada do que cada
    turno tem licença para escolher — manhã só fala de hoje, noite só de amanhã.
    """
    if turno is None:
        return True
    if turno not in TURNOS:
        raise ValueError(f'turno desconhecido: {turno!r}')
    return item.get('format') in PUBLICAVEIS[turno]

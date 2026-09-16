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

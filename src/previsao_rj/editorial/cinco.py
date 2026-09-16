"""As cinco previsões que todo Reel mostra (decisão do proprietário, 16/09/2026).

Todo Reel, de qualquer apresentador e de qualquer formato, mostra pelo menos
cinco previsões na tela, sempre cobrindo:

    Niterói · Centro do Rio · Zona Sul · Baixada · Campo Grande

Cada região é representada pelo ponto-âncora dela na coleta (sample_tier 1 em
config/locais_rj.yaml). Se o ponto preferido faltar, vale outro da mesma zona.
Se a região inteira faltar na coleta, a vaga é preenchida por outro ponto
coletado, com o nome REAL dele: número de uma região nunca é inventado nem
emprestado de outra.
"""
from __future__ import annotations

import math
from typing import Any

MINIMO = 5

# (rótulo na tela, ids preferidos em ordem, zonas aceitas como reserva)
REGIOES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ('Niterói', ('icarai', 'niteroi_centro', 'piratininga', 'sao_francisco', 'charitas',
                 'camboinhas', 'itaipu', 'itacoatiara'), ('niteroi_baia', 'niteroi_oceanica')),
    ('Centro do Rio', ('centro_rio', 'lapa', 'gloria', 'saude_gamboa'), ('centro',)),
    ('Zona Sul', ('copacabana', 'ipanema', 'botafogo', 'flamengo', 'leblon', 'urca'), ('zona_sul',)),
    ('Baixada', ('duque_de_caxias', 'nova_iguacu', 'sao_joao_de_meriti', 'belford_roxo',
                 'nilopolis', 'mesquita'), ('baixada',)),
    ('Campo Grande', ('campo_grande',), ()),
)


def _valido(loc: dict[str, Any]) -> bool:
    return all(isinstance(loc.get(k), (int, float)) and math.isfinite(loc[k])
               for k in ('min_c', 'max_c'))


def _linha(nome: str, loc: dict[str, Any], regiao: str | None) -> dict[str, Any]:
    return {'nome': nome, 'min': loc['min_c'], 'max': loc['max_c'],
            'id': loc.get('id'), 'regiao': regiao}


def cinco_regioes(locations: list[dict[str, Any]], minimo: int = MINIMO) -> list[dict[str, Any]]:
    """Linhas do cartão de resumo: as cinco regiões fixas, na ordem, e o
    complemento até `minimo` se alguma faltar na coleta."""
    validos = [l for l in locations if _valido(l)]
    por_id = {l.get('id'): l for l in validos}
    usados: set[str] = set()
    linhas: list[dict[str, Any]] = []
    for rotulo, ids, zonas in REGIOES:
        escolhido = next((por_id[i] for i in ids if i in por_id and i not in usados), None)
        if escolhido is None and zonas:
            escolhido = next((l for l in validos if l.get('zone') in zonas
                              and l.get('id') not in usados), None)
        if escolhido is not None:
            usados.add(escolhido.get('id'))
            linhas.append(_linha(rotulo, escolhido, rotulo))
    for loc in validos:
        if len(linhas) >= minimo:
            break
        if loc.get('id') in usados:
            continue
        usados.add(loc.get('id'))
        linhas.append(_linha(loc['name'], loc, None))
    return linhas


def faltando(linhas: list[dict[str, Any]]) -> list[str]:
    """Regiões obrigatórias que não entraram (para o log do render)."""
    presentes = {l['regiao'] for l in linhas}
    return [r for r, _, _ in REGIOES if r not in presentes]


# Na fala, o nome curto: o cartão já diz "Centro do Rio".
FALADO = {'Centro do Rio': 'Centro'}


def fala_resumo(linhas: list[dict[str, Any]], quando: str = '') -> str:
    """Frase curta para o cartão: as regiões e a faixa das máximas.

    Curta de propósito — o Reel tem teto de 40 s (e o roteiro, de ~80
    palavras) e o cartão já mostra cada número. Ex.: "Niterói, Centro, Zona
    Sul, Baixada e Campo Grande: de 27 a 36 graus."
    """
    nomes = [FALADO.get(l['nome'], l['nome']) for l in linhas]
    lista = nomes[0] if len(nomes) == 1 else ', '.join(nomes[:-1]) + ' e ' + nomes[-1]
    maximas = [l['max'] for l in linhas]
    lo, hi = min(maximas), max(maximas)
    faixa = f'máxima de {lo:g} graus' if lo == hi else f'de {lo:g} a {hi:g} graus'
    prefixo = f'{quando.strip()}, em ' if quando.strip() else ''
    texto = f'{prefixo}{lista}: {faixa}.'
    return texto[0].upper() + texto[1:]

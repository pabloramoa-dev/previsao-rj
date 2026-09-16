"""Preposição certa antes do nome do lugar: na Tijuca, no Méier, em Copacabana.

Usado pela fala do Reel, pela legenda e pelas respostas do atendimento. Fica em
`geo` (e sem dependência nenhuma) porque o serviço do Render importa daqui e não
pode carregar o motor editorial.
"""
from __future__ import annotations

# "Em Barra da Tijuca", "Em Centro": o Reel de 15/09/2026 saiu assim. Bairro do
# Rio tem artigo — na Tijuca, no Méier, em Copacabana — e a fala precisa dele.
# Nome fora das listas fica com "em", que é o certo para município e para a
# maior parte dos bairros sem artigo.
_NA = {'Barra da Tijuca', 'Tijuca', 'Glória', 'Lapa', 'Penha', 'Urca',
       'Ilha do Governador', 'Freguesia', 'Taquara', 'Vila Isabel',
       'Saúde e Gamboa'}
_NO = {'Centro', 'Centro de Niterói', 'Méier', 'Maracanã', 'Flamengo', 'Leblon',
       'Grajaú', 'Joá', 'Pechincha', 'Recreio dos Bandeirantes', 'Recreio',
       'Alto da Boa Vista', 'Nilton Santos', 'Rio', 'Rio de Janeiro'}
_NAS = {'Barcas - Niterói', 'Barcas - Praça XV'}


def em_local(nome: str, inicio: bool = False) -> str:
    """'Barra da Tijuca' -> 'na Barra da Tijuca'; 'Centro' -> 'no Centro'."""
    if nome in _NA:
        prep = 'na'
    elif nome in _NO:
        prep = 'no'
    elif nome in _NAS:
        prep = 'nas'
    else:
        prep = 'em'
    texto = f'{prep} {nome}'
    return texto[0].upper() + texto[1:] if inicio else texto


def em_locais(nomes: list[str], inicio: bool = False) -> str:
    """['Barra da Tijuca', 'Campo Grande'] -> 'na Barra da Tijuca e em Campo Grande'."""
    partes = [em_local(n) for n in nomes]
    texto = partes[0] if len(partes) == 1 else ', '.join(partes[:-1]) + ' e ' + partes[-1]
    return texto[0].upper() + texto[1:] if inicio else texto

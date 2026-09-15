"""Corta o roteiro para caber na janela editorial do Reel (§16.1).

Por que isso existe: em 15/09/2026 a primeira execução do fluxo diário montou um
`rio_antes_de_sair` com oito batidas e 43,2 s de narração. O QA de vídeo recusou
(o teto é 40 s) e o Reel não saiu. Não foi bug de render — foi um dia com muita
informação: contraste térmico, resumo das cidades, chuva E vento, cada um com a
sua batida. Quanto mais o Rio tem para contar, mais longo o Reel fica, e num dia
de alerta o Reel simplesmente não seria publicado.

A saída não é afrouxar o QA. É decidir, com critério explícito, o que sai do ar
quando não cabe tudo — que é exatamente o trabalho de um editor.

Ordem de corte, do primeiro a cair para o último:

1. `resumo` — a lista de máximas por cidade. É a batida mais redundante: o
   cartão na tela já mostra os números, e o gancho principal já deu a leitura.
2. `gancho` secundário — a segunda leitura numérica do dia.
3. incerteza (`nenhum` no meio do roteiro) — o aviso de cenário instável.
4. `alerta` — só cai se nada mais couber. Vento forte é a informação que muda
   o comportamento de quem assiste.

Nunca caem: a abertura e o CTA. Sem abertura não há gancho nos primeiros
segundos, e sem CTA o Reel não pede nada de quem assistiu.

E o corte para em três batidas. Se nem assim couber — caso que exigiria linhas
de 15 s, coisa que a narração não produz —, o roteiro sai longo e o
`scripts/qa_video.py` recusa. É a resposta certa: um Reel de abertura mais CTA,
sem previsão nenhuma, é pior do que não publicar.
"""
from __future__ import annotations

from typing import Any, Iterable

# Janela do Plano Mestre §16.1. O piso não é decorativo: Reel curto demais entrega
# menos do que promete e o corte não pode ser tão agressivo a ponto de produzir isso.
PISO = 25.0
TETO = 38.0

# Maior = sai antes.
PESO = {
    'resumo': 4,
    'gancho': 3,
    'nenhum': 2,
    'cidade': 2,
    'alerta': 1,
    'cta': 0,
}


def _ordem_de_corte(batidas: list[dict[str, Any]]) -> list[int]:
    """Índices candidatos a sair, do primeiro ao último a cair.

    A primeira e a última batida ficam de fora da lista: não são candidatas.
    Empate no peso é resolvido pelo índice maior — corta-se o mais tardio,
    preservando a ordem de leitura do que sobra.
    """
    miolo = range(1, max(len(batidas) - 1, 1))
    return sorted(miolo,
                  key=lambda i: (-PESO.get(batidas[i].get('tipo'), 2), -i))


def cortar_para_janela(batidas: list[dict[str, Any]],
                       duracoes: Iterable[float],
                       teto: float = TETO,
                       piso: float = PISO) -> tuple[list[dict[str, Any]], list[int]]:
    """Devolve (batidas que ficam, índices cortados).

    Só corta o necessário para passar do teto. Na primeira passada, evita cortes
    que derrubariam o Reel abaixo do piso; se ainda assim não couber, faz uma
    segunda passada sem essa proteção — melhor um Reel curto no ar do que um
    Reel longo recusado pelo QA.
    """
    duracoes = list(duracoes)
    if len(duracoes) != len(batidas):
        raise ValueError('uma duração por batida, sempre')

    total = sum(duracoes)
    if total <= teto or len(batidas) <= 3:
        return list(batidas), []

    fora: set[int] = set()
    for protegendo_o_piso in (True, False):
        for i in _ordem_de_corte(batidas):
            if total <= teto:
                break
            if i in fora:
                continue
            se_cortar = total - duracoes[i]
            if protegendo_o_piso and se_cortar < piso:
                continue
            if len(batidas) - len(fora) - 1 < 3:
                continue
            fora.add(i)
            total = se_cortar
        if total <= teto:
            break

    return ([b for i, b in enumerate(batidas) if i not in fora], sorted(fora))

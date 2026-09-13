"""Faixas verticais do quadro 9:16 — geometria pura, sem manim.

Mora fora de `scene.py` de proposito: scene.py importa manim, que nao esta no
requirements de teste. Aqui a regra de layout fica testavel no CI, que e onde
uma regressao de enquadramento precisa aparecer — nao no olho de quem assiste.

O quadro tem frame_height 14.222 (|y| <= 7.11), mas a camera fecha ate
ZOOM_MIN=0.82 no push-in: so |y| <= 5.83 e realmente visivel. Tudo aqui e
medido nessa area util.

Regra central: painel da faixa superior e ancorado pela borda de CIMA, nunca
pelo centro. A altura varia muito de um cartao para o outro (uma faixa fina de
UV tem 0.7; a tabela das cinco cidades tem 5.5), e ancorar pelo centro fazia o
cartao alto subir por cima da marca do perfil.
"""
from __future__ import annotations

VISIVEL = 5.83              # |y| maximo que a camera enquadra no zoom minimo

Y_MARCA = 5.45              # centro da marca @previsaorj
ALTURA_MARCA = 0.71

TOPO_PAINEL = 4.95          # borda de cima dos paineis da faixa superior

Y_SELO = 3.95               # centro do selo (titulo / cidade da vez)
ALTURA_SELO = 1.54

Y_CENTRAL = 1.2             # gancho e CTA ocupam o meio da tela

# Faixa vertical da cabeca do apresentador, ja escalado e posicionado.
ROSTO_BASE, ROSTO_TOPO = 0.40, 2.45

# Batidas em que o apresentador SAI de cena: o painel fica com a tela inteira.
# Sem isto, o gancho e o CTA aparecem em cima do rosto dele.
SOZINHOS = ("resumo", "gancho", "cta")

# Alturas medidas dos paineis (scripts/medir_layout.py). Servem de referencia
# para o teste de enquadramento; o render usa a altura real do mobject.
ALTURAS = {
    "faixa": 0.71,          # umidade, uv, preparar, alerta, fecho
    "cidade": 1.12,
    "chuva": 2.30,
    "duplo": 2.40,          # duas_cidades, amplitude, sensacao
    "cta": 2.35,
    "gancho": 3.38,
    "resumo": 5.52,
}


def base_marca() -> float:
    """Borda de baixo da marca do perfil."""
    return Y_MARCA - ALTURA_MARCA / 2


def faixa_painel(altura: float) -> tuple[float, float]:
    """(base, topo) de um painel ancorado pela borda de cima."""
    return TOPO_PAINEL - altura, TOPO_PAINEL


def cobre_marca(altura: float) -> bool:
    return faixa_painel(altura)[1] > base_marca()


def cobre_rosto(altura: float) -> bool:
    base, topo = faixa_painel(altura)
    return topo > ROSTO_BASE and base < ROSTO_TOPO


def sai_da_tela(altura: float) -> bool:
    return faixa_painel(altura)[0] < -VISIVEL


def juntar_janelas(janelas, folga: float = 0.6):
    """Funde janelas vizinhas de saida de cena.

    Gancho e CTA costumam ser batidas seguidas. Sem fundir, o apresentador
    volta ao quadro e sai de novo em menos de meio segundo — o olho le como
    falha de montagem, nao como intencao.
    """
    ordenadas = sorted(janelas)
    if not ordenadas:
        return []
    fundidas = [list(ordenadas[0])]
    for ini, fim in ordenadas[1:]:
        if ini <= fundidas[-1][1] + folga:
            fundidas[-1][1] = max(fundidas[-1][1], fim)
        else:
            fundidas.append([ini, fim])
    return [tuple(j) for j in fundidas]

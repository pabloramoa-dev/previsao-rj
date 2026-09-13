"""Mede a caixa de cada painel e confere contra as faixas de layout.

Existe porque os numeros em `render/characters/layout.py` sao MEDIDOS, nao
escolhidos: a altura de um cartao depende da fonte, do texto e do zoom. Rodar
isto depois de mexer em qualquer cartao mostra se ele ainda cabe na faixa.

Precisa do manim (requirements/characters.txt), entao nao roda no CI — o teste
que roda no CI e tests/test_layout.py, sobre as constantes.

    python scripts/medir_layout.py
"""
from manim import config

from src.previsao_rj.render.characters import layout as LAY

config.frame_width = 8.0
config.frame_height = 14.222

from src.previsao_rj.render.characters import rj_cast as RJ  # noqa: E402
from src.previsao_rj.render.characters import visual as P  # noqa: E402

CINCO = [{"nome": f"Cidade {i}", "min": 20, "max": 30} for i in range(5)]


def medir():
    """Altura real de cada cartao, no mesmo tamanho em que o render desenha."""
    return {
        "cidade": P.card_cidade("Copacabana", 22, 24, "chuva").height,
        "cta": P.cta_seguir().height,
        "gancho": P.numero_gigante("90%", "CHANCE DE CHUVA").height,
        "resumo": P.card_resumo(CINCO, altura_max=5.6, buff=0.34, fs_titulo=32).height,
    }


def main():
    print(f"marca ocupa ate y={LAY.base_marca():.2f}")
    presenter = RJ.presenter("bira")["grupo"].scale(1.1).move_to([0, -0.55, 0])
    print(f"apresentador: topo={presenter.get_top()[1]:.2f} base={presenter.get_bottom()[1]:.2f}")
    problemas = 0
    for nome, altura in sorted(medir().items(), key=lambda x: x[1]):
        base, topo = LAY.faixa_painel(altura)
        marca = LAY.cobre_marca(altura)
        rosto = LAY.cobre_rosto(altura) and nome not in LAY.SOZINHOS
        fora = LAY.sai_da_tela(altura)
        if marca or rosto or fora:
            problemas += 1
        print(f"{nome:<8} altura={altura:5.2f}  ocupa {base:6.2f} -> {topo:5.2f}"
              f"  marca={marca}  rosto={rosto}  fora_da_tela={fora}")
    raise SystemExit(1 if problemas else 0)


if __name__ == "__main__":
    main()

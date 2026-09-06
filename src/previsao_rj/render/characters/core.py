"""
dvh_lib — Biblioteca visual do canal Delegacia Vinte e Quatro Horas (DVH).

Personagens, cenários e objetos desenhados por código em Manim. Traço grosso,
cabeça grande, rosto expressivo, fundo colorido. Custo zero, sem IA de imagem,
personagem sempre idêntico entre cenas.

Cada função de personagem devolve um dict com:
    grupo : VGroup do personagem inteiro (é o que você adiciona/anima)
    cab   : o círculo do rosto (âncora pra balões, óculos, etc.)
    oe,od : olhos (pra susto: .animate.scale(...))
    boca  : a boca (invisibilize e passe pra anexar_lipsync se o personagem fala)

Regra de ouro do movimento: NADA congela. Todo personagem em cena recebe o
updater `respirar()` pra ter um leve sobe-e-desce contínuo. Cenas paradas com
self.wait() sem updater dão a sensação de "travou" — foi reclamação real.
"""
from manim import *
import numpy as np

# ---- paleta oficial ----
PT = BLACK
AMAR = "#ffd240"
VERM = "#e2483c"
VERD = "#32a06e"
NAVY = "#0b0d16"
MUT = "#9aa3bd"
FONTE = "Poppins"   # instalada pelo setup_ambiente.sh (fonts-google-poppins)


# =====================================================================
#  LEGENDA — banda escura translúcida + texto branco Poppins Bold.
#  NÃO use contorno preto grosso no texto: embola as letras (erro real,
#  "a legenda ficou ruim"). A banda dá contraste; o texto fica limpo.
# =====================================================================
def legenda(txt, font_size=30, cor=WHITE):
    t = Text(txt, font=FONTE, weight=BOLD, font_size=font_size, color=cor)
    if t.width > 11.2:
        t.scale(11.2 / t.width)
    band = RoundedRectangle(width=t.width + 0.7, height=t.height + 0.4,
                            corner_radius=0.14, fill_color=BLACK,
                            fill_opacity=0.7, stroke_width=0)
    return VGroup(band, t).to_edge(DOWN, buff=0.4)


# =====================================================================
#  UPDATERS DE MOVIMENTO CONTÍNUO
# =====================================================================
def respirar(G, amp=0.05, periodo=2.6):
    """Sobe-e-desce sutil e infinito. Chame em TODO personagem em cena."""
    st = {'t': 0.0, 'o': 0.0}
    def _r(mo, dt):
        st['t'] += dt
        novo = amp * np.sin(st['t'] * TAU / periodo)
        mo.shift(UP * (novo - st['o']))
        st['o'] = novo
    G.add_updater(_r)
    return _r


def digitar(maoE, maoD, amp=0.05, vel=3.0):
    """Mãos alternadas subindo/descendo — pra quem digita no PC/teclado."""
    st = {'t': 0.0, 'oe': 0.0, 'od': 0.0}
    def _d(mo, dt):
        st['t'] += dt
        ne = amp * np.sin(st['t'] * TAU * vel)
        nd = amp * np.sin(st['t'] * TAU * vel + PI)
        maoE.shift(UP * (ne - st['oe'])); st['oe'] = ne
        maoD.shift(UP * (nd - st['od'])); st['od'] = nd
    return _d   # anexe no grupo: G.add_updater(digitar(g["maoE"], g["maoD"]))


# =====================================================================
#  CENÁRIOS  (fundo do frame inteiro)
# =====================================================================
def _grad(cores, direcao=UP):
    W = config.frame_width; H = config.frame_height
    r = Rectangle(width=W + 2, height=H + 2, fill_opacity=1, stroke_width=0).set_color(cores)
    r.set_sheen_direction(direcao)
    return r



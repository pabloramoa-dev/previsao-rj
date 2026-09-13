"""
previsao_lib — Seu Ranzinza e os cenários de tempo para o @previsaorj.

Mesma filosofia da dvh_lib: tudo desenhado por código, traço grosso, cabeça
grande, personagem SEMPRE idêntico entre os vídeos. Custo zero, sem IA de imagem.

Personagem: SEU RANZINZA — velho careca de tufos grisalhos, sobrancelhas
franzidas, óculos de meia-lua na ponta do nariz, bigode grosso, camisa xadrez
vermelha, suspensórios e bengala. Reclama de todo tipo de tempo.

Regra de ouro herdada: NADA congela. Todo personagem em cena leva respirar().
"""
from manim import *
import numpy as np
import sys, os

from . import core as L

PT = L.PT
FONTE = L.FONTE
AMAR = L.AMAR
VERM = L.VERM
VERD = L.VERD

# A câmera fecha até 0.82 do quadro no push-in inicial e na volta do loop.
# Logo, a largura REALMENTE visível o tempo todo é 8.0*0.82 = 6.56 — e não 8.0.
# Todo texto tem que caber aqui, senão sai da tela nos primeiros segundos.
ZOOM_MIN = 0.82
SEGURA = 8.0 * ZOOM_MIN - 0.55        # ~5.99: largura útil com margem

# Largura máxima de QUALQUER texto ou cartaz.
# A câmera abre em ZOOM_INICIAL, então nos primeiros e últimos segundos só se vê
# essa fração do frame. Dimensionar pelo frame cheio (8.0) faz a legenda sair da
# tela justamente na abertura — que é onde a retenção se decide.
ZOOM_INICIAL = 0.90
LARG_SEGURA = 6.2            # 8.0 * 0.90 = 7.2 visíveis; 6.2 + moldura = 6.8

# A câmera fecha até 0.82 do quadro no push-in inicial e na volta do loop.
# Tudo que é texto precisa caber NESSE enquadramento, não no quadro cheio —
# senão a legenda sai da tela durante os 2 primeiros segundos, que é justo
# quando mais gente está assistindo.
ZOOM_MIN = 0.82
MARGEM = 0.55          # respiro pras bordas e pra interface do Instagram


def larg_segura():
    return config.frame_width * ZOOM_MIN - MARGEM


GRIS = "#d8d4cd"      # cabelo/bigode grisalho
PELE = "#f4d9bd"      # rosto (o velho tem rosto com cor, não branco)
XADREZ = "#b8433a"    # camisa xadrez vermelha
XADREZ_ESC = "#8a2f28"


# =====================================================================
#  SEU RANZINZA
# =====================================================================
def ranzinza(humor="bravo"):
    """O velho da previsão do tempo.

    humor: "bravo" (padrão, sobrancelha franzida + boca virada pra baixo),
           "desconfiado" (uma sobrancelha erguida),
           "resmungando" (boca torta).

    Devolve dict com grupo, cab, oe, od, boca (pro lip sync), bengala, maoD.
    """
    # --- cabeça ---
    cab = Circle(radius=0.9, stroke_color=PT, stroke_width=15,
                 fill_color=PELE, fill_opacity=1).shift(UP * 1.4)
    c = cab.get_center()

    # careca: calota de pele + tufos grisalhos nas laterais e atrás das orelhas
    tufoE = Ellipse(width=0.55, height=0.75, fill_color=GRIS, fill_opacity=1,
                    stroke_color=PT, stroke_width=8).move_to(c + LEFT * 0.78 + UP * 0.18)
    tufoD = Ellipse(width=0.55, height=0.75, fill_color=GRIS, fill_opacity=1,
                    stroke_color=PT, stroke_width=8).move_to(c + RIGHT * 0.78 + UP * 0.18)
    # 3 fiozinhos rebeldes no alto da careca
    fios = VGroup(*[
        ArcBetweenPoints(c + UP * 0.88 + RIGHT * (i * 0.16 - 0.16),
                         c + UP * 1.18 + RIGHT * (i * 0.16 - 0.06),
                         angle=PI / 2.5).set_stroke(GRIS, 7)
        for i in range(3)])

    # orelhas
    orE = Ellipse(width=0.22, height=0.34, fill_color=PELE, fill_opacity=1,
                  stroke_color=PT, stroke_width=7).move_to(c + LEFT * 0.92 + DOWN * 0.12)
    orD = Ellipse(width=0.22, height=0.34, fill_color=PELE, fill_opacity=1,
                  stroke_color=PT, stroke_width=7).move_to(c + RIGHT * 0.92 + DOWN * 0.12)

    # sobrancelhas grossas e FRANZIDAS (V invertido = bravo)
    if humor == "desconfiado":
        sobE = Line(c + LEFT * 0.52 + UP * 0.30, c + LEFT * 0.16 + UP * 0.40,
                    stroke_color=GRIS, stroke_width=13)
        sobD = Line(c + RIGHT * 0.16 + UP * 0.52, c + RIGHT * 0.52 + UP * 0.46,
                    stroke_color=GRIS, stroke_width=13)
    else:
        sobE = Line(c + LEFT * 0.54 + UP * 0.42, c + LEFT * 0.14 + UP * 0.24,
                    stroke_color=GRIS, stroke_width=13)
        sobD = Line(c + RIGHT * 0.14 + UP * 0.24, c + RIGHT * 0.54 + UP * 0.42,
                    stroke_color=GRIS, stroke_width=13)

    # olhos com pé de galinha (marcas de idade)
    oe = Dot(c + LEFT * 0.32 + UP * 0.04, radius=0.10, color=PT)
    od = Dot(c + RIGHT * 0.32 + UP * 0.04, radius=0.10, color=PT)
    ruga = VGroup(
        Line(c + LEFT * 0.62 + UP * 0.10, c + LEFT * 0.50 + UP * 0.16, stroke_color=PT, stroke_width=4),
        Line(c + LEFT * 0.62 + UP * 0.00, c + LEFT * 0.50 + UP * 0.02, stroke_color=PT, stroke_width=4),
        Line(c + RIGHT * 0.50 + UP * 0.16, c + RIGHT * 0.62 + UP * 0.10, stroke_color=PT, stroke_width=4),
        Line(c + RIGHT * 0.50 + UP * 0.02, c + RIGHT * 0.62 + UP * 0.00, stroke_color=PT, stroke_width=4))

    # óculos de MEIA-LUA na ponta do nariz (abaixo dos olhos — é o charme dele)
    lenteE = Arc(radius=0.26, start_angle=PI, angle=PI,
                 arc_center=c + LEFT * 0.32 + DOWN * 0.06).set_stroke(PT, 7)
    lenteD = Arc(radius=0.26, start_angle=PI, angle=PI,
                 arc_center=c + RIGHT * 0.32 + DOWN * 0.06).set_stroke(PT, 7)
    barraE = Line(c + LEFT * 0.58 + DOWN * 0.06, c + LEFT * 0.06 + DOWN * 0.06, stroke_color=PT, stroke_width=7)
    barraD = Line(c + RIGHT * 0.06 + DOWN * 0.06, c + RIGHT * 0.58 + DOWN * 0.06, stroke_color=PT, stroke_width=7)
    hasteE = Line(c + LEFT * 0.58 + DOWN * 0.06, c + LEFT * 0.90 + DOWN * 0.02, stroke_color=PT, stroke_width=5)
    hasteD = Line(c + RIGHT * 0.58 + DOWN * 0.06, c + RIGHT * 0.90 + DOWN * 0.02, stroke_color=PT, stroke_width=5)
    oculos = VGroup(lenteE, lenteD, barraE, barraD, hasteE, hasteD)

    # nariz batatudo
    nariz = Ellipse(width=0.26, height=0.30, fill_color="#e8b89a", fill_opacity=1,
                    stroke_color=PT, stroke_width=6).move_to(c + DOWN * 0.20)

    # bigode grosso grisalho (duas metades)
    bigE = Ellipse(width=0.42, height=0.22, fill_color=GRIS, fill_opacity=1,
                   stroke_color=PT, stroke_width=5).move_to(c + DOWN * 0.44 + LEFT * 0.19)
    bigD = Ellipse(width=0.42, height=0.22, fill_color=GRIS, fill_opacity=1,
                   stroke_color=PT, stroke_width=5).move_to(c + DOWN * 0.44 + RIGHT * 0.19)
    bigode = VGroup(bigE, bigD)

    # BOCA — virada pra baixo. É esta que vai pro lip sync.
    if humor == "resmungando":
        boca = ArcBetweenPoints(c + DOWN * 0.60 + LEFT * 0.22, c + DOWN * 0.68 + RIGHT * 0.22,
                                angle=-PI / 5).set_stroke(PT, 8)
    else:
        boca = ArcBetweenPoints(c + DOWN * 0.62 + LEFT * 0.24, c + DOWN * 0.62 + RIGHT * 0.24,
                                angle=-PI / 3).set_stroke(PT, 8)

    # --- corpo ---
    pesc = Line(cab.get_bottom(), cab.get_bottom() + DOWN * 0.22, stroke_color=PT, stroke_width=15)
    t = pesc.get_end()

    camisa = Polygon(t + LEFT * 0.62, t + RIGHT * 0.62,
                     t + DOWN * 1.55 + RIGHT * 0.86, t + DOWN * 1.55 + LEFT * 0.86,
                     fill_color=XADREZ, fill_opacity=1, stroke_color=PT, stroke_width=10)
    # trama do xadrez: linhas verticais e horizontais mais escuras
    trama = VGroup()
    for dx in [-0.5, -0.17, 0.17, 0.5]:
        trama.add(Line(t + RIGHT * dx + DOWN * 0.06, t + RIGHT * dx * 1.35 + DOWN * 1.5,
                       stroke_color=XADREZ_ESC, stroke_width=6))
    for dy in [0.35, 0.75, 1.15]:
        w = 0.62 + (dy / 1.55) * 0.24
        trama.add(Line(t + DOWN * dy + LEFT * w, t + DOWN * dy + RIGHT * w,
                       stroke_color=XADREZ_ESC, stroke_width=6))
    gola = VGroup(
        Line(t + LEFT * 0.22, t + DOWN * 0.38 + LEFT * 0.04, stroke_color=PT, stroke_width=6),
        Line(t + RIGHT * 0.22, t + DOWN * 0.38 + RIGHT * 0.04, stroke_color=PT, stroke_width=6))
    # suspensórios
    susp = VGroup(
        Line(t + LEFT * 0.34 + DOWN * 0.30, t + LEFT * 0.44 + DOWN * 1.5, stroke_color="#3b4a2f", stroke_width=11),
        Line(t + RIGHT * 0.34 + DOWN * 0.30, t + RIGHT * 0.44 + DOWN * 1.5, stroke_color="#3b4a2f", stroke_width=11))

    # braços
    omb = t + DOWN * 0.25
    be = Line(omb + LEFT * 0.5, omb + DOWN * 0.9 + LEFT * 0.72, stroke_color=PT, stroke_width=15)
    bd = Line(omb + RIGHT * 0.5, omb + DOWN * 0.72 + RIGHT * 0.82, stroke_color=PT, stroke_width=15)
    maoE = Dot(be.get_end(), radius=0.13, color=PELE).set_stroke(PT, 5)
    maoD = Dot(bd.get_end(), radius=0.13, color=PELE).set_stroke(PT, 5)

    # calça + pernas + chinelo
    q = t + DOWN * 1.55
    calca = Polygon(q + LEFT * 0.86, q + RIGHT * 0.86, q + DOWN * 0.5 + RIGHT * 0.72, q + DOWN * 0.5 + LEFT * 0.72,
                    fill_color="#4b5566", fill_opacity=1, stroke_color=PT, stroke_width=8)
    pe = Line(q + DOWN * 0.45 + LEFT * 0.34, q + DOWN * 1.5 + LEFT * 0.5, stroke_color="#4b5566", stroke_width=20)
    pd = Line(q + DOWN * 0.45 + RIGHT * 0.34, q + DOWN * 1.5 + RIGHT * 0.5, stroke_color="#4b5566", stroke_width=20)
    chE = Ellipse(width=0.46, height=0.2, fill_color="#6b4a2f", fill_opacity=1,
                  stroke_color=PT, stroke_width=5).move_to(pe.get_end() + DOWN * 0.04 + LEFT * 0.08)
    chD = Ellipse(width=0.46, height=0.2, fill_color="#6b4a2f", fill_opacity=1,
                  stroke_color=PT, stroke_width=5).move_to(pd.get_end() + DOWN * 0.04 + RIGHT * 0.08)

    # bengala na mão direita
    beng = VGroup(
        Line(maoD.get_center() + UP * 0.1, maoD.get_center() + DOWN * 1.75, stroke_color="#7a5230", stroke_width=11),
        Arc(radius=0.22, start_angle=PI, angle=-PI, arc_center=maoD.get_center() + UP * 0.1 + RIGHT * 0.22)
        .set_stroke("#7a5230", 11))

    grupo = VGroup(pesc, calca, pe, pd, chE, chD, camisa, trama, susp, gola,
                   be, bd, beng, maoE, maoD,
                   orE, orD, tufoE, tufoD, cab, fios,
                   nariz, oculos, sobE, sobD, oe, od, ruga, bigode, boca)
    return dict(grupo=grupo, cab=cab, oe=oe, od=od, boca=boca, bigode=bigode,
                oculos=oculos, bengala=beng, maoE=maoE, maoD=maoD, sobE=sobE, sobD=sobD, bracoE=be, bracoD=bd)


# =====================================================================
#  CENÁRIO: a varanda do Seu Ranzinza, com o céu do dia
# =====================================================================
CEUS = {
    "sol":        (["#8fd0f0", "#4a9fd4"], "#ffe08a"),
    "nublado":    (["#b9c4cf", "#7d8b99"], "#cfd8e0"),
    "chuva":      (["#7d8b9c", "#4a5666"], "#9aa8b8"),
    "tempestade": (["#5c6472", "#2f3540"], "#7d8797"),
    "frio":       (["#a9c4d8", "#6e8598"], "#dfe8ef"),
    # Céu do Reel das 18h (Dona Maria). NÃO é uma condição de tempo: é a HORA
    # em que ela grava. O tempo de que ela fala é o de amanhã, e vive nos cards
    # — se o fundo seguisse a previsão, um dia de chuva colocaria chuva caindo
    # em cima dela às 18h de um dia seco.
    "entardecer": (["#ffb27a", "#e2685f"], "#ffd9a0"),
}


def ceu(condicao="sol"):
    """Fundo do frame inteiro conforme a condição do tempo."""
    cores, _ = CEUS.get(condicao, CEUS["sol"])
    W = config.frame_width
    H = config.frame_height
    r = Rectangle(width=W + 2, height=H + 2, fill_opacity=1, stroke_width=0).set_color(cores)
    r.set_sheen_direction(UP)
    return r


def _nuvem(escala=1.0, cor=WHITE, op=0.92):
    n = VGroup(*[Circle(radius=rr, fill_color=cor, fill_opacity=op, stroke_width=0)
                 for rr in [0.38, 0.55, 0.44]])
    n[0].shift(LEFT * 0.55)
    n[2].shift(RIGHT * 0.55)
    return n.scale(escala)


def varanda(condicao="sol"):
    """Cenário completo da varanda do Seu Ranzinza.

    Devolve um DICT (não um VGroup) porque a animação precisa de alças soltas:
        grupo  -> o fundo inteiro, pra dar self.add()
        raios  -> os raios do sol (giram)  | None se não houver sol
        nuvens -> as nuvens (deslizam)
        astro  -> o sol/lua, pra pulsar
    Ligue tudo de uma vez com `animar_cenario(scene, cen, condicao)`.
    """
    cores, _ = CEUS.get(condicao, CEUS["sol"])
    W = config.frame_width
    H = config.frame_height
    g = VGroup()
    g.add(ceu(condicao))

    raios = astro = None
    nuvens = VGroup()

    if condicao == "sol":
        astro = Circle(radius=0.55, fill_color="#ffe08a", fill_opacity=1, stroke_width=0)
        raios = VGroup(*[Line(RIGHT * 0.68, RIGHT * 1.02, stroke_color="#ffe08a", stroke_width=8)
                         .rotate(a, about_point=ORIGIN) for a in np.arange(0, TAU, TAU / 12)])
        sol = VGroup(raios, astro).move_to([W / 2 - 1.4, H / 2 - 1.6, 0])
        g.add(sol)
        nuvens.add(_nuvem(0.8).move_to([-W / 2 + 1.6, H / 2 - 2.4, 0]))
    elif condicao == "frio":
        astro = Circle(radius=0.5, fill_color="#f2f6f9", fill_opacity=0.85, stroke_width=0)
        g.add(astro.move_to([W / 2 - 1.4, H / 2 - 1.6, 0]))
        nuvens.add(_nuvem(1.0, "#e7eef4", 0.8).move_to([-W / 2 + 1.7, H / 2 - 2.1, 0]),
                   _nuvem(0.75, "#e7eef4", 0.7).move_to([W / 2 - 2.0, H / 2 - 3.1, 0]))
    else:
        cor_n = "#c3ccd6" if condicao == "nublado" else "#8d98a6"
        nuvens.add(_nuvem(1.15, cor_n, 0.95).move_to([-W / 2 + 2.0, H / 2 - 1.7, 0]),
                   _nuvem(0.9, cor_n, 0.95).move_to([W / 2 - 1.8, H / 2 - 2.5, 0]),
                   _nuvem(1.0, cor_n, 0.9).move_to([0.4, H / 2 - 3.4, 0]))
    g.add(nuvens)

    # morros do Sul Fluminense (silhueta em camadas)
    base_y = -H / 2 + 3.8
    for (dy, cor, esc) in [(0.0, "#4a6b52", 1.0), (-0.5, "#3a5742", 1.25)]:
        pts = [[-W / 2 - 1, base_y + dy - 2, 0]]
        xs = np.linspace(-W / 2 - 1, W / 2 + 1, 9)
        alturas = [0.5, 1.5, 0.9, 1.9, 1.1, 1.7, 0.8, 1.4, 0.6]
        for x, a in zip(xs, alturas):
            pts.append([x, base_y + dy + a / esc, 0])
        pts.append([W / 2 + 1, base_y + dy - 2, 0])
        g.add(Polygon(*pts, fill_color=cor, fill_opacity=1, stroke_width=0))

    piso_y = -3.15  # plano de apoio ajustado ao enquadramento de corpo inteiro do RJ
    g.add(Rectangle(width=W + 2, height=4.6, fill_color="#9c8b7a", fill_opacity=1,
                    stroke_width=0).move_to([0, piso_y - 2.3, 0]))
    gc = VGroup()
    gc.add(Line([-W / 2 - 1, piso_y, 0], [W / 2 + 1, piso_y, 0], stroke_color="#6f5a44", stroke_width=16))
    gc.add(Line([-W / 2 - 1, piso_y - 0.75, 0], [W / 2 + 1, piso_y - 0.75, 0], stroke_color="#6f5a44", stroke_width=10))
    for x in np.arange(-W / 2 - 0.5, W / 2 + 1, 1.15):
        gc.add(Line([x, piso_y, 0], [x, piso_y - 1.5, 0], stroke_color="#6f5a44", stroke_width=9))
    g.add(gc)

    vaso = VGroup(
        Polygon([-0.35, 0, 0], [0.35, 0, 0], [0.26, -0.6, 0], [-0.26, -0.6, 0],
                fill_color="#b4674a", fill_opacity=1, stroke_color=PT, stroke_width=6),
        *[Ellipse(width=0.22, height=0.6, fill_color="#3f8a52", fill_opacity=1,
                  stroke_color=PT, stroke_width=4).rotate(a).shift(UP * 0.45 + RIGHT * a * 0.5)
          for a in [-0.5, 0.0, 0.5]])
    g.add(vaso.move_to([W / 2 - 1.1, piso_y - 1.3, 0]))

    return dict(grupo=g, raios=raios, nuvens=nuvens, astro=astro, piso_y=piso_y)


# =====================================================================
#  MOVIMENTO DO CENÁRIO — nada de fundo estático
# =====================================================================
def sol_girando(raios, vel=0.22, duracao=None, dentes=12):
    """Gira os raios. Com `duracao`, ajusta a velocidade pra terminar num
    múltiplo exato do passo angular entre raios (TAU/dentes) — visualmente
    idêntico ao início, fechando o loop."""
    if duracao:
        passo = TAU / dentes
        n = max(1, round(vel * duracao / passo))
        vel = n * passo / duracao
    raios.add_updater(lambda mo, dt: mo.rotate(vel * dt))


def nuvens_deslizando(nuvens, vel=0.16, duracao=None):
    """Cada nuvem atravessa o céu e reaparece do outro lado.

    A posição é ANALÍTICA (x0 + (v*t) módulo L), não incremental com um "if"
    de wrap. Isso importa porque, com `duracao`, a velocidade é ajustada pra
    v*duracao ser um múltiplo exato de L — aí no último frame a nuvem está
    EXATAMENTE onde começou e o loop do Reel não tem emenda. Com o wrap por
    condição a distância real do ciclo não batia com a calculada, e sobrava
    um deslocamento visível no replay.
    """
    W = config.frame_width
    L = W + 4.0                       # comprimento do ciclo (entra e sai da tela)
    for k, n in enumerate(nuvens):
        c = n.get_center()
        n.x0, n.y0 = float(c[0]), float(c[1])
        v = vel * (0.7 + 0.3 * k)
        if duracao:
            voltas = max(1, round(v * duracao / L))
            v = voltas * L / duracao
        n.vel = v
    st = {"t": 0.0}

    def _andar(mo, dt):
        st["t"] += dt
        for n in mo:
            x = n.x0 + (n.vel * st["t"]) % L
            if x > W / 2 + 2.0:       # já saiu pela direita: volta pela esquerda
                x -= L
            n.move_to([x, n.y0, 0])
    nuvens.add_updater(_andar)


def chuva(scene, n=55, vel=6.0, cor="#cfe4f5", forte=False, vento=0.35):
    """Gotas caindo em loop infinito. Devolve o VGroup."""
    W = config.frame_width
    H = config.frame_height
    rng = np.random.default_rng(7)
    gotas = VGroup()
    for _ in range(n):
        x = rng.uniform(-W / 2 - 1.0, W / 2 + 1.0)
        y = rng.uniform(-H / 2, H / 2)
        comp = rng.uniform(0.22, 0.45) * (1.5 if forte else 1.0)
        gt = Line([x, y, 0], [x - comp * vento, y - comp, 0],
                  stroke_color=cor, stroke_width=4 if forte else 3)
        gt.set_opacity(rng.uniform(0.5, 0.95))
        gt.vel = vel * rng.uniform(0.8, 1.3)
        gotas.add(gt)

    def _cair(mo, dt):
        for gt in mo:
            gt.shift(DOWN * gt.vel * dt + LEFT * gt.vel * vento * dt)
            if gt.get_center()[1] < -H / 2 - 0.5:
                gt.shift(UP * (H + 1) + RIGHT * rng.uniform(0.5, 2.5))
    gotas.add_updater(_cair)
    scene.add(gotas)
    return gotas


def poca(scene, piso_y, n=3):
    """Poças no piso da varanda com ondulação — reforça que está chovendo."""
    W = config.frame_width
    rng = np.random.default_rng(11)
    pocas = VGroup()
    for i in range(n):
        x = rng.uniform(-W / 2 + 1, W / 2 - 1)
        p = Ellipse(width=rng.uniform(1.1, 1.8), height=0.22, fill_color="#6f8ea8",
                    fill_opacity=0.55, stroke_width=0).move_to([x, piso_y - 1.9, 0])
        p.fase = rng.uniform(0, TAU)
        p.w0 = p.width
        pocas.add(p)
    st = {"t": 0.0}

    def _ondular(mo, dt):
        st["t"] += dt
        for p in mo:
            alvo = p.w0 * (1 + 0.06 * np.sin(st["t"] * 2.2 + p.fase))
            p.stretch_to_fit_width(alvo)
    pocas.add_updater(_ondular)
    scene.add(pocas)
    return pocas


def relampago(scene, periodo=3.4, semente=5):
    """Clarão branco de tempestade: 2 piscadas rápidas, depois espera.

    Um flash só lê como falha de render; dois em sequência lê como raio.
    """
    W = config.frame_width
    H = config.frame_height
    flash = Rectangle(width=W + 2, height=H + 2, fill_color=WHITE,
                      fill_opacity=0, stroke_width=0)
    rng = np.random.default_rng(semente)
    st = {"t": 0.0, "prox": rng.uniform(1.0, periodo)}

    def _piscar(mo, dt):
        st["t"] += dt
        d = st["t"] - st["prox"]
        op = 0.0
        if 0 <= d < 0.09:
            op = 0.75 * (1 - d / 0.09)
        elif 0.16 <= d < 0.30:
            op = 0.5 * (1 - (d - 0.16) / 0.14)
        elif d >= 0.30:
            st["prox"] = st["t"] + rng.uniform(periodo * 0.6, periodo * 1.5)
        mo.set_opacity(op)
    flash.add_updater(_piscar)
    scene.add(flash)
    return flash


def nevoa(scene, janelas=None, n=7, semente=3, op_max=0.20):
    """Bancos de névoa que atravessam a cena. `janelas` = [(ini,fim)] em que
    aparecem; None = o vídeo inteiro."""
    rng = np.random.default_rng(semente)
    g = VGroup(*[
        Ellipse(width=rng.uniform(3.0, 5.5), height=rng.uniform(0.5, 0.9),
                fill_color=WHITE, fill_opacity=1, stroke_width=0)
        .move_to([rng.uniform(-3, 3), rng.uniform(-4.5, 1.5), 0])
        for _ in range(n)])
    g.set_opacity(0 if janelas else op_max)
    st = {"t": 0.0}

    def _deriva(mo, dt):
        st["t"] += dt
        mo.shift(RIGHT * 0.3 * dt)
        if janelas:
            op = 0.0
            for ini, fim in janelas:
                if ini <= st["t"] <= fim + 0.6:
                    sobe = min(1.0, (st["t"] - ini) / 0.5)
                    desce = min(1.0, max(0.0, (fim + 0.6 - st["t"]) / 0.6))
                    op = max(op, op_max * sobe * desce)
            mo.set_opacity(op)
    g.add_updater(_deriva)
    scene.add(g)
    return g


def ondas_calor(scene, piso_y, n=5):
    """Linhas onduladas subindo do piso — o ar tremendo de calor."""
    W = config.frame_width
    rng = np.random.default_rng(19)
    g = VGroup()
    for i in range(n):
        x = rng.uniform(-W / 2 + 1, W / 2 - 1)
        c = VMobject(stroke_color="#ffe9b0", stroke_width=5).set_points_smoothly(
            [[x, piso_y - 2.0, 0], [x + 0.18, piso_y - 1.4, 0],
             [x - 0.18, piso_y - 0.8, 0], [x + 0.10, piso_y - 0.2, 0]])
        c.set_opacity(0.35)
        c.fase = rng.uniform(0, TAU)
        g.add(c)
    st = {"t": 0.0}

    def _tremer(mo, dt):
        st["t"] += dt
        for c in mo:
            c.set_opacity(0.35 * (0.5 + 0.5 * np.sin(st["t"] * 1.8 + c.fase)))
            c.shift(RIGHT * 0.12 * dt * np.sin(st["t"] * 3 + c.fase))
    g.add_updater(_tremer)
    scene.add(g)
    return g


def animar_cenario(scene, cen, condicao, calor=False, duracao=None):
    """Liga todo o movimento de fundo de uma vez, conforme a condição do dia.

    `duracao` (segundos do vídeo) faz os elementos LENTOS — nuvens e sol —
    fecharem o ciclo no último frame, pro loop do Reel não ter emenda. Chuva e
    névoa não precisam: são rápidas e aleatórias, o olho não acompanha gota.
    """
    if cen.get("raios") is not None:
        sol_girando(cen["raios"], duracao=duracao)
    if len(cen["nuvens"]):
        nuvens_deslizando(cen["nuvens"], duracao=duracao)
    if condicao == "chuva":
        chuva(scene, n=60, vel=6.5)
        poca(scene, cen["piso_y"])
    elif condicao == "tempestade":
        chuva(scene, n=85, vel=8.5, forte=True, vento=0.55)
        poca(scene, cen["piso_y"], n=4)
        relampago(scene)
    elif condicao == "frio":
        nevoa(scene, n=6, op_max=0.14)
    if calor:
        ondas_calor(scene, cen["piso_y"])


# =====================================================================
#  AÇÕES E ADEREÇOS DO SEU RANZINZA
#  Todas seguem a mesma convenção: recebem `janelas` = [(ini, fim)] em
#  segundos da narração, e só agem dentro delas. Fora, o personagem fica
#  na pose normal (mas nunca parado — o respirar() continua rodando).
# =====================================================================
def copo_agua(v, escala=1.0):
    """Copo com água na mão esquerda do velho."""
    m = v["maoE"].get_center()
    vidro = RoundedRectangle(width=0.34, height=0.46, corner_radius=0.05,
                             fill_color="#cfe8f5", fill_opacity=0.55,
                             stroke_color=PT, stroke_width=6)
    agua = Rectangle(width=0.26, height=0.26, fill_color="#4aa3d8", fill_opacity=0.9,
                     stroke_width=0).align_to(vidro, DOWN).shift(UP * 0.06)
    g = VGroup(vidro, agua).scale(escala).move_to(m + UP * 0.16)
    return g


def beber(v, copo, janelas, dur=1.6, tilt=0.55):
    """Levanta o copo até a boca, inclina, e volta — dentro de cada janela.

    A pose é calculada por INTEIRO a cada frame a partir de `f` (0 = mão em
    repouso, 1 = copo na boca) e reconstruída com `become`. A versão anterior
    aplicava `rotate` incremental enquanto bebia: a rotação acumulava e não
    zerava, então o copo ficava torto pro resto do vídeo — e ainda quebrava o
    loop, porque o último frame não batia com o primeiro.
    """
    base = copo.copy()
    st = {"t": 0.0}

    def _beber(mo, dt):
        st["t"] += dt
        f = 0.0
        for ini, _fim in janelas:
            d = st["t"] - ini
            if 0 <= d < dur:
                f = max(f, np.sin(d / dur * PI) ** 0.7)   # sobe, segura, desce
        mao = v["maoE"].get_center() + UP * 0.16
        alvo = v["boca"].get_center() + DOWN * 0.05 + LEFT * 0.05
        pos = mao + (alvo - mao) * f
        ang = -tilt * max(0.0, (f - 0.55) / 0.45)         # só inclina no fim
        mo.become(base.copy().rotate(ang).move_to(pos))
    copo.add_updater(_beber)
    return copo


def cachecol(v, cor="#8a2f28"):
    """Cachecol no pescoço — dia de frio."""
    c = v["cab"].get_bottom() + DOWN * 0.24
    faixa = RoundedRectangle(width=1.05, height=0.30, corner_radius=0.1,
                             fill_color=cor, fill_opacity=1, stroke_color=PT,
                             stroke_width=6).move_to(c)
    ponta = RoundedRectangle(width=0.26, height=0.72, corner_radius=0.08,
                             fill_color=cor, fill_opacity=1, stroke_color=PT,
                             stroke_width=6).move_to(c + DOWN * 0.48 + RIGHT * 0.34)
    return VGroup(faixa, ponta)


def tremer(G, janelas, amp=0.045, vel=17.0):
    """Tremedeira de frio: vibração horizontal rápida dentro das janelas."""
    st = {"t": 0.0, "o": 0.0}

    def _tremer(mo, dt):
        st["t"] += dt
        dentro = any(ini <= st["t"] <= fim for ini, fim in janelas)
        novo = amp * np.sin(st["t"] * vel) if dentro else 0.0
        mo.shift(RIGHT * (novo - st["o"]))
        st["o"] = novo
    G.add_updater(_tremer)


def bafo(scene, v, janelas, n=3):
    """Vapor saindo da boca no frio — sobe, cresce e some, em ciclo."""
    rng = np.random.default_rng(23)
    g = VGroup(*[Circle(radius=0.10, fill_color=WHITE, fill_opacity=0, stroke_width=0)
                 for _ in range(n)])
    fases = [rng.uniform(0, 1) for _ in range(n)]
    st = {"t": 0.0}
    ciclo = 1.8

    def _bafo(mo, dt):
        st["t"] += dt
        dentro = any(ini <= st["t"] <= fim for ini, fim in janelas)
        origem = v["boca"].get_center() + DOWN * 0.05 + LEFT * 0.25
        for k, p in enumerate(mo):
            if not dentro:
                p.set_opacity(0)
                continue
            f = ((st["t"] / ciclo) + fases[k]) % 1.0
            p.move_to(origem + LEFT * (0.9 * f) + UP * (0.5 * f))
            p.set_width(0.20 + 0.55 * f)
            p.set_opacity(0.55 * (1 - f) * min(1.0, f * 5))
    g.add_updater(_bafo)
    scene.add(g)
    return g


def apontar(v, janelas, alvo=UP * 2.2 + RIGHT * 1.6, dur=1.4):
    """Levanta o braço direito apontando (a Dona Maria mostrando o cartaz).

    Pose calculada por inteiro a cada frame a partir de `f` e reconstruída com
    `become` — nunca incremental, senão o braço não volta e o loop quebra.

    A pose é ancorada na CABEÇA, não numa coordenada fixa do quadro. A primeira
    versão guardava a posição absoluta da mão e a reescrevia todo frame; quando
    `sair_de_cena` levava o personagem para fora, a mão era puxada de volta ao
    ponto antigo e sobrava um braço esticado no meio da tela — o mesmo conflito
    que o docstring de `sair_de_cena` descreve: dois updaters escrevendo
    posição absoluta brigam. Guardando o deslocamento em relação à cabeça, a
    pose viaja junto com o corpo e continua exata no retorno.
    """
    mao = v["maoD"]
    cab = v["cab"]
    base = mao.copy()
    repouso = mao.get_center() - cab.get_center()
    st = {"t": 0.0}

    def _apontar(mo, dt):
        st["t"] += dt
        f = 0.0
        for ini, _fim in janelas:
            d = st["t"] - ini
            if 0 <= d < dur:
                f = max(f, np.sin(d / dur * PI) ** 0.6)
        mo.become(base.copy().move_to(cab.get_center() + repouso + alvo * f))
    mao.add_updater(_apontar)


def abanar(v, janelas, amp=0.30, vel=6.0):
    """Abana a mão direita perto do rosto — dia de calor."""
    mao = v["maoD"]
    st = {"t": 0.0, "o": 0.0}

    def _abanar(mo, dt):
        st["t"] += dt
        dentro = any(ini <= st["t"] <= fim for ini, fim in janelas)
        novo = amp * np.sin(st["t"] * vel) if dentro else 0.0
        mo.shift(RIGHT * (novo - st["o"]))
        st["o"] = novo
    mao.add_updater(_abanar)


def suor(scene, v, janelas, n=2):
    """Gotas de suor pulando da testa — calor forte."""
    g = VGroup(*[Ellipse(width=0.14, height=0.20, fill_color="#7ec8f0",
                         fill_opacity=0, stroke_color=PT, stroke_width=3)
                 for _ in range(n)])
    st = {"t": 0.0}
    ciclo = 1.5

    def _suor(mo, dt):
        st["t"] += dt
        dentro = any(ini <= st["t"] <= fim for ini, fim in janelas)
        c = v["cab"].get_center()
        for k, p in enumerate(mo):
            if not dentro:
                p.set_opacity(0)
                continue
            f = ((st["t"] / ciclo) + k * 0.5) % 1.0
            lado = LEFT if k % 2 else RIGHT
            p.move_to(c + lado * 0.72 + UP * (0.45 - 0.5 * f) + lado * (0.35 * f))
            p.set_opacity(0.9 * (1 - f))
    g.add_updater(_suor)
    scene.add(g)
    return g


def guarda_chuva(v, cor="#2f6b8a", raio=2.05, altura=1.75, achatamento=0.62):
    """Guarda-chuva aberto acima da cabeça.

    `raio` e `altura` generosos de propósito: ele precisa cobrir os OMBROS, não
    só o alto da cabeça, senão parece chapéu e a chuva de fundo passa rente ao
    rosto. Com raio 2.05 a cúpula ultrapassa a silhueta do personagem dos dois
    lados, que é o que faz o desenho ler como "protegido".
    """
    c = v["cab"].get_center()
    topo = c + UP * altura
    cupula = VGroup()
    for i, (a0, a1) in enumerate([(PI, PI * 0.75), (PI * 0.75, PI * 0.5),
                                  (PI * 0.5, PI * 0.25), (PI * 0.25, 0)]):
        cor_i = cor if i % 2 == 0 else "#245670"
        cupula.add(AnnularSector(inner_radius=0, outer_radius=raio,
                                 start_angle=a0, angle=a1 - a0,
                                 fill_color=cor_i, fill_opacity=1,
                                 stroke_color=PT, stroke_width=7)
                   .move_arc_center_to(topo))
    # varetas, pra não ficar um disco chapado
    varetas = VGroup(*[Line(topo, topo + np.array([np.cos(a) * raio, np.sin(a) * raio, 0]),
                            stroke_color=PT, stroke_width=4)
                       for a in [PI * 0.75, PI * 0.5, PI * 0.25]])
    domo = VGroup(cupula, varetas)
    domo.stretch(achatamento, dim=1, about_point=topo)
    haste = Line(topo, topo + DOWN * (altura + 0.55), stroke_color="#7a5230", stroke_width=10)
    cabo = Arc(radius=0.24, start_angle=PI, angle=-PI,
               arc_center=topo + DOWN * (altura + 0.55) + RIGHT * 0.24).set_stroke("#7a5230", 10)
    ponta = Dot(domo.get_top() + UP * 0.06, radius=0.09, color=PT)
    return VGroup(domo, haste, cabo, ponta)


def pingar_guarda_chuva(scene, gc, por_lado=2):
    """Gotas escorrendo do guarda-chuva — SÓ pelas duas pontas.

    Antes as gotas eram distribuídas por toda a largura da cúpula, inclusive no
    meio: caíam exatamente no rosto do personagem e pareciam suor. Água de
    guarda-chuva escorre pela borda, não pelo centro — então elas nascem nas
    extremidades, que ficam fora da silhueta do corpo.
    """
    rng = np.random.default_rng(31)
    esq, dir_ = gc.get_left()[0], gc.get_right()[0]
    borda_y = gc.get_bottom()[1] + 0.35
    xs = ([esq + 0.10 + k * 0.16 for k in range(por_lado)] +
          [dir_ - 0.10 - k * 0.16 for k in range(por_lado)])
    g = VGroup(*[Line(ORIGIN, DOWN * 0.20, stroke_color="#cfe4f5", stroke_width=4)
                 for _ in xs])
    fases = [rng.uniform(0, 1) for _ in xs]
    st = {"t": 0.0}

    def _pingar(mo, dt):
        st["t"] += dt
        for k, p in enumerate(mo):
            f = ((st["t"] / 1.1) + fases[k]) % 1.0
            p.move_to([xs[k], borda_y - 2.4 * f, 0])
            p.set_opacity(0.85 * (1 - f * 0.7))
    g.add_updater(_pingar)
    scene.add(g)
    return g


def vestir(scene, v, condicao, janelas_frio=None, janelas_calor=None,
           janelas_beber=None, com_guarda_chuva=True):
    """Aplica adereços e ações conforme o dia. Devolve os mobjects criados
    (o chamador precisa deles pra ordem de desenho).

    `com_guarda_chuva=False` desliga o adereço mesmo em cenário de chuva. É o
    caso da Dona Maria: o cenário dela é sempre o entardecer de HOJE e a chuva
    de que ela fala é a de AMANHÃ, então não há água caindo pra ela se proteger.
    """
    extras = {}
    G = v["grupo"]
    if com_guarda_chuva and condicao in ("chuva", "tempestade"):
        gc = guarda_chuva(v)
        scene.add(gc)
        pingar_guarda_chuva(scene, gc)
        extras["guarda_chuva"] = gc
    if condicao == "frio":
        ca = cachecol(v)
        scene.add(ca)
        extras["cachecol"] = ca
        janelas = janelas_frio or [(0, 1e9)]
        tremer(G, janelas)
        bafo(scene, v, janelas)
    if janelas_calor:
        abanar(v, janelas_calor)
        suor(scene, v, janelas_calor)
    if janelas_beber:
        copo = copo_agua(v)
        scene.add(copo)
        beber(v, copo, janelas_beber)
        extras["copo"] = copo
    return extras


# =====================================================================
#  LEGENDA KARAOKÊ — terço central, palavra por palavra
#  Fonte da recomendação: 65% assiste sem som; legenda no centro (não no
#  rodapé, onde a interface do Instagram cobre) e palavra em destaque
#  seguram bem mais a atenção que uma frase estática embaixo.
# =====================================================================
def legenda_karaoke(txt, ini, fim, y=-1.6, fs=54, larg=None, destaque=None,
                    por_bloco=3):
    """Devolve [(t0, t1, mobject)] pra jogar direto na trilha_temporal.

    Quebra a fala em blocos de até `por_bloco` palavras e, dentro de cada
    bloco, acende uma palavra de cada vez. O tempo de cada palavra é
    proporcional ao número de letras — aproximação boa o bastante, já que
    o Kokoro nos dá o início e o fim exatos da FRASE.
    """
    destaque = destaque or AMAR
    larg = SEGURA - 0.6 if larg is None else larg   # desconta a moldura da banda
    palavras = txt.split()
    if not palavras:
        return []
    pesos = [max(2, len(p)) for p in palavras]
    total = sum(pesos)
    dur = max(0.2, fim - ini)

    # tempo de início de cada palavra
    t_ini, acc = [], 0.0
    for p in pesos:
        t_ini.append(ini + dur * acc / total)
        acc += p
    t_ini.append(fim)

    saida = []
    for b0 in range(0, len(palavras), por_bloco):
        bloco = palavras[b0:b0 + por_bloco]
        for k in range(len(bloco)):
            partes = VGroup(*[
                Text(w, font=FONTE, weight=BOLD, font_size=fs,
                     color=destaque if j == k else WHITE)
                for j, w in enumerate(bloco)]).arrange(RIGHT, buff=0.22)
            if partes.width > larg:
                partes.scale(larg / partes.width)
            band = RoundedRectangle(width=partes.width + 0.6,
                                    height=partes.height + 0.5,
                                    corner_radius=0.18, fill_color=BLACK,
                                    fill_opacity=0.72, stroke_width=0)
            partes.move_to(band)
            saida.append((t_ini[b0 + k], t_ini[b0 + k + 1],
                          VGroup(band, partes).move_to([0, y, 0])))
    return saida


def numero_gigante(txt, sub=None, cor=None, fs=170):
    """O gancho: o número do dia ocupando a tela. É o primeiro frame do Reel.

    A decisão de deslizar acontece em ~1,5s, então o vídeo não pode abrir com
    o personagem parado dando bom-dia — abre com o dado mais extremo do dia.
    """
    cor = cor or AMAR
    util = SEGURA - 0.9                       # desconta a moldura larga do cartaz
    n = Text(txt, font=FONTE, weight=BOLD, font_size=fs, color=cor)
    if n.width > util:
        n.scale(util / n.width)
    itens = [n]
    if sub:
        s = Text(sub, font=FONTE, weight=BOLD, font_size=54, color=WHITE)
        if s.width > util:
            s.scale(util / s.width)
        itens.append(s)
    g = VGroup(*itens).arrange(DOWN, buff=0.30)
    band = RoundedRectangle(width=g.width + 0.9, height=g.height + 0.9,
                            corner_radius=0.3, fill_color=BLACK,
                            fill_opacity=0.72, stroke_color=WHITE, stroke_width=5)
    g.move_to(band)
    return VGroup(band, g)


def entrada_estalo(mob, ini, dur=0.42, escala_ini=2.1):
    """Updater que faz o mobject ESTALAR na tela (grande -> tamanho normal).

    É o `zoom punch` do dvh_fx adaptado pro objeto em vez da câmera: dá
    impacto no primeiro frame sem exigir MovingCameraScene pro elemento.
    """
    base = mob.copy()
    st = {"t": 0.0}

    def _estalo(mo, dt):
        st["t"] += dt
        d = st["t"] - ini
        if d < 0:
            mo.set_opacity(0)
            return
        if d >= dur:
            mo.become(base)
            mo.remove_updater(_estalo)
            return
        f = d / dur
        e = escala_ini + (1.0 - escala_ini) * (1 - (1 - f) ** 3)   # ease-out
        mo.become(base.copy().scale(e))
        mo.set_opacity(min(1.0, f * 3))
    mob.add_updater(_estalo)
    return mob


def camera_push_in(scene, dur=2.2, zoom_ini=None, deriva=0.015,
                   duracao=None, volta=0.7):
    """Técnica 4: movimento nos primeiros frames.

    A câmera começa fechada no rosto e ABRE até o enquadramento cheio nos
    primeiros segundos — o olho entende que algo está acontecendo antes de
    ler qualquer texto. Depois segue uma deriva lentíssima pra nunca ficar
    100% parada. Exige MovingCameraScene.
    """
    frame = scene.camera.frame
    W = config.frame_width
    zoom_ini = ZOOM_INICIAL if zoom_ini is None else zoom_ini
    frame.set(width=W * zoom_ini)
    alvo_y = 1.0
    frame.move_to([0, alvo_y, 0])
    st = {"t": 0.0}

    def _cam(mo, dt):
        st["t"] += dt
        t = st["t"]
        if t < dur:                                   # abre (push-in inicial)
            f = t / dur
            e = 1 - (1 - f) ** 3
            mo.set(width=W * (zoom_ini + (1.0 - zoom_ini) * e))
            mo.move_to([0, alvo_y * (1 - e), 0])
        elif duracao and t > duracao - volta:         # fecha de novo, pro loop
            f = min(1.0, (t - (duracao - volta)) / volta)
            e = f * f
            mo.set(width=W * (1.0 + (zoom_ini - 1.0) * e))
            mo.move_to([0, alvo_y * e, 0])
        else:
            d = t - dur
            mo.set(width=W * (1.0 + deriva * np.sin(d * 0.35)))
    frame.add_updater(_cam)
    return frame


ICONES = {
    "sol": "☀", "nublado": "☁", "chuva": "🌧", "tempestade": "⛈", "frio": "❄",
}


def card_cidade(cidade, tmin, tmax, condicao="sol", largura=None):
    """Cartão translúcido com cidade e min/máx. Legível em tela de celular."""
    largura = SEGURA if largura is None else largura
    largura = LARG_SEGURA if largura is None else largura
    largura = largura if largura is not None else larg_segura()
    nome = Text(cidade, font=FONTE, weight=BOLD, font_size=42, color=WHITE)
    temps = Text(f"{int(tmin)}°  /  {int(tmax)}°", font=FONTE, weight=BOLD,
                 font_size=52, color=AMAR)
    linha = VGroup(nome, temps).arrange(RIGHT, buff=0.5)
    if linha.width > largura - 0.7:
        linha.scale((largura - 0.7) / linha.width)
    band = RoundedRectangle(width=largura, height=linha.height + 0.55,
                            corner_radius=0.2, fill_color=BLACK, fill_opacity=0.68,
                            stroke_color=WHITE, stroke_width=3)
    linha.move_to(band)
    return VGroup(band, linha)


def card_resumo(cidades, titulo="AS CINCO PRINCIPAIS", altura_max=2.9,
                buff=0.16, fs_titulo=26):
    """O quadro com as cinco cidades e min/máx de cada, tudo de uma vez.

    Por que TUDO de uma vez, e não um cartão por cidade: quem abre o Reel quer
    a temperatura DA SUA cidade. Num carrossel de cinco cartões ele espera até
    a vez dela — e a maioria desliza antes. Num quadro só, acha a linha dele no
    primeiro segundo e fica pelo resto.

    `altura_max` não é decoração. A câmera fecha até ZOOM_MIN, o que deixa
    visível só |y| <= 5.83, e o cartão vive centrado na faixa do painel. Passar
    disso corta a primeira linha justamente durante o push-in. O conteúdo é
    montado no tamanho natural e depois encolhido pra caber — assim acrescentar
    uma cidade a mais nunca estoura o quadro, só aperta as linhas.

    `cidades`: lista de dicts do dia.json (nome, min, max).
    """
    largura = larg_segura()
    util = largura - 0.7
    linhas = VGroup()
    if titulo:
        t = Text(titulo, font=FONTE, weight=BOLD, font_size=fs_titulo, color=AMAR)
        if t.width > util:            # "AMANHÃ NAS CINCO PRINCIPAIS" não cabe em 26
            t.scale_to_fit_width(util)
        linhas.add(t)
    nomes = [Text(c["nome"], font=FONTE, weight=BOLD, font_size=38, color=WHITE)
             for c in cidades]
    temps = [Text(f"{int(c['min'])}°  /  {int(c['max'])}°", font=FONTE,
                  weight=BOLD, font_size=38, color=AMAR) for c in cidades]

    # UM fator de escala pra TODOS os nomes, calculado pelo mais comprido.
    # Encolher só o nome que não coube — que foi a primeira versão — deixa
    # "Volta Redonda" e "Barra do Piraí" visivelmente menores que "Resende" na
    # mesma lista, e o quadro parece defeito de renderização, não escolha.
    if nomes:
        larg_nome = util - max(t.width for t in temps) - 0.35
        maior = max(n.width for n in nomes)
        if maior > larg_nome:
            for n in nomes:
                n.scale(larg_nome / maior)

    for nome, temp in zip(nomes, temps):
        # os dois extremos ancorados nas bordas: a coluna de temperaturas fica
        # alinhada entre as linhas mesmo com nomes de larguras muito diferentes
        # ("Quatis" e "Barra do Piraí" na mesma lista)
        linha = VGroup(nome, temp)
        nome.move_to(LEFT * (util / 2), aligned_edge=LEFT)
        temp.move_to(RIGHT * (util / 2), aligned_edge=RIGHT)
        linhas.add(linha)
    linhas.arrange(DOWN, buff=buff)
    if linhas.height > altura_max - 0.5:
        linhas.scale((altura_max - 0.5) / linhas.height)
    band = RoundedRectangle(width=largura, height=linhas.height + 0.5,
                            corner_radius=0.2, fill_color=BLACK, fill_opacity=0.78,
                            stroke_color=WHITE, stroke_width=3)
    linhas.move_to(band)
    return VGroup(band, linhas)


def sair_de_cena(portador, mobs, ini, fim, dur=0.7, desloc=6.2, folga=0.25):
    """Tira o personagem do quadro entre `ini` e `fim`, e o traz de volta.

    Serve à batida do resumo: enquanto ele lê as cinco cidades, o quadro delas
    fica sozinho no centro da tela. O personagem parado no canto durante
    dezessete segundos não acrescenta nada — sair e voltar dá um respiro de
    montagem e devolve a tela inteira ao conteúdo.

    Três cuidados que o código carrega:

    - **Sai pela direita, não pra baixo.** Descer atravessa o piso da varanda e
      lê como bug; sair de lado lê como "ele foi ali e já volta".
    - **Deslocamento por DIFERENÇA**, nunca posição absoluta. `respirar()` já
      mexe no mesmo grupo pelo mesmo caminho; dois updaters que escrevessem
      posição absoluta brigariam e o personagem tremeria.
    - **Volta com `folga` antes do fim da batida.** Se voltasse exatamente no
      fim, ele reapareceria no mesmo frame em que o quadro sai — dois
      movimentos no mesmo instante que o olho lê como corte seco.

    `portador` é quem carrega o updater (o grupo do personagem); `mobs` é tudo
    que precisa viajar junto — inclui os adereços que não seguem o personagem
    sozinhos (guarda-chuva, cachecol).
    """
    t_volta = max(ini + dur, fim - folga - dur)
    st = {"t": 0.0, "x": 0.0}

    def _suave(f):                       # começa e termina devagar
        f = min(1.0, max(0.0, f))
        return f * f * (3 - 2 * f)

    def _sair(_mo, dt):
        st["t"] += dt
        t = st["t"]
        if t < ini or t > t_volta + dur:
            f = 0.0
        elif t < ini + dur:
            f = _suave((t - ini) / dur)
        elif t < t_volta:
            f = 1.0
        else:
            f = _suave(1 - (t - t_volta) / dur)
        alvo = desloc * f
        d = alvo - st["x"]
        if d:
            for m in mobs:
                m.shift(RIGHT * d)
            st["x"] = alvo

    portador.add_updater(_sair)
    return _sair


def legenda_vertical(txt, y=-4.2, cor=WHITE, fs=46, larg=None):
    """Legenda do formato 9:16 — banda escura + Poppins Bold branco, SEM stroke.
    (Lição #4: contorno grosso embola as letras.)"""
    larg = SEGURA - 0.6 if larg is None else larg
    larg = LARG_SEGURA if larg is None else larg
    larg = (larg if larg is not None else larg_segura()) - 0.65
    t = Text(txt, font=FONTE, weight=BOLD, font_size=fs, color=cor)
    if t.width > larg:
        t.scale(larg / t.width)
    band = RoundedRectangle(width=t.width + 0.6, height=t.height + 0.45,
                            corner_radius=0.16, fill_color=BLACK, fill_opacity=0.72,
                            stroke_width=0)
    return VGroup(band, t).move_to([0, y, 0])


def trilha_temporal(itens, pop=0.16):
    """Troca mobjects pelo RELÓGIO DA CENA — o mesmo que move o lip sync.

    itens: lista de (ini, fim, mobject) em segundos da narração.

    Por que não usar play/wait encadeados: cada animação é arredondada pro frame
    mais próximo, e ao longo de 30s isso empurra as trocas ~0,4s pra frente — a
    legenda desgruda da fala no fim. Aqui a troca é lida do tempo absoluto, então
    é frame-exata e idêntica à do lip sync. Bônus: pra gerar o vídeo do dia basta
    montar essa lista a partir do segs.json, sem coreografar nada.

    `pop` = duração do estica-e-assenta na entrada (dá vida, evita corte seco).
    """
    grupo = VGroup()
    st = {"t": 0.0, "i": -2, "t0": 0.0}

    def upd(mo, dt):
        st["t"] += dt
        agora = st["t"]
        idx = -1
        for k, (ini, fim, _m) in enumerate(itens):
            if ini <= agora < fim:
                idx = k
                break
        if idx != st["i"]:
            mo.become(itens[idx][2].copy() if idx >= 0 else VGroup())
            st["i"] = idx
            st["t0"] = agora
        elif idx >= 0:
            # estica-e-assenta nos primeiros instantes depois da troca
            dtt = agora - st["t0"]
            if dtt < pop:
                base = itens[idx][2]
                f = dtt / pop
                escala = 1.0 + 0.10 * np.sin(f * PI)
                mo.become(base.copy().scale(escala))

    grupo.add_updater(upd)
    return grupo


def marca_dagua():
    """Selo do perfil no topo — identidade visual fixa."""
    t = Text("@previsaorj", font=FONTE, weight=BOLD, font_size=28, color=WHITE)
    band = RoundedRectangle(width=t.width + 0.5, height=t.height + 0.3,
                            corner_radius=0.14, fill_color=BLACK, fill_opacity=0.55,
                            stroke_width=0)
    return VGroup(band, t)


def selo_cidade(nome, rotulo="HOJE EM"):
    """A cidade da vez, escrita grande acima da cabeça do personagem.

    Existe por causa da GRADE do perfil, não do vídeo. Na grade os dez últimos
    Reels são dez miniaturas do mesmo velho na mesma varanda — nada ali diz de
    que cidade é cada um. Este selo é o que diferencia uma miniatura da outra.

    Três decisões:

    - **Na faixa do painel (y ≈ 4.5), não no topo do quadro.** A grade exibe o
      Reel recortado em 3:4, ou seja, corta ~240px de cima e de baixo do 9:16.
      A marca d'água (y 6.35) fica FORA desse recorte — colocar o nome junto
      dela seria escrever pra ninguém. Em y 4.5 o nome sobrevive ao corte.

    - **Só nas primeiras batidas.** Nessa altura o gancho está no centro da
      tela e a faixa do painel está livre; a partir da batida `cidade` o
      cartão de mínima/máxima ocupa o mesmo lugar e o selo sai. O primeiro
      frame continua limpo (`ABERTURA`), então o loop segue sem emenda — quem
      escolhe o frame da capa é o `thumb_offset` do postar_reel.py.

    - **Caixa alta e corpo grande.** Na grade o quadro aparece com ~330px de
      largura, menos de um terço do render. O que não se lê nesse tamanho não
      existe: por isso o nome vem em 56 e o rótulo, que é acessório, em 26.
    """
    largura = larg_segura()
    rot = Text(rotulo, font=FONTE, weight=BOLD, font_size=26, color=AMAR)
    cid = Text(nome.upper(), font=FONTE, weight=BOLD, font_size=56, color=WHITE)
    miolo = VGroup(rot, cid).arrange(DOWN, buff=0.08)
    if miolo.width > largura - 0.7:
        miolo.scale((largura - 0.7) / miolo.width)
    band = RoundedRectangle(width=largura, height=miolo.height + 0.5,
                            corner_radius=0.2, fill_color=BLACK, fill_opacity=0.68,
                            stroke_color=WHITE, stroke_width=3)
    miolo.move_to(band)
    return VGroup(band, miolo)


# =====================================================================
#  DONA MARIA — o bloco prático da hora do almoço
#  Contraponto do Ranzinza: ele reclama de manhã, ela resolve à tarde.
#  Paleta quente, traço igual (mesmo mundo), postura aberta.
# =====================================================================
PELE_M = "#f7dcc4"
GRIS_M = "#dedad3"
AVENTAL = "#e8b04b"
AVENTAL_ESC = "#c98f2e"
BLUSA_M = "#7aa9c4"


def dona_maria(humor="simpatica"):
    """A vizinha que já sabe como vai ser o dia de amanhã.

    humor: "simpatica" (padrão, sorriso aberto) | "conspirando" (sorriso torto,
    uma sobrancelha erguida — pra quando ela fala do Ranzinza).

    Devolve dict com grupo, cab, oe, od, boca (pro lip sync), maoE, maoD.
    """
    cab = Circle(radius=0.9, stroke_color=PT, stroke_width=15,
                 fill_color=PELE_M, fill_opacity=1).shift(UP * 1.4)
    c = cab.get_center()

    # cabelo grisalho emoldurando + COQUE no alto
    moldura = VGroup(
        Arc(radius=0.98, start_angle=PI * 0.08, angle=PI * 0.84,
            arc_center=c).set_stroke(GRIS_M, 22),
        Ellipse(width=0.46, height=0.78, fill_color=GRIS_M, fill_opacity=1,
                stroke_color=PT, stroke_width=7).move_to(c + LEFT * 0.80 + UP * 0.10),
        Ellipse(width=0.46, height=0.78, fill_color=GRIS_M, fill_opacity=1,
                stroke_color=PT, stroke_width=7).move_to(c + RIGHT * 0.80 + UP * 0.10))
    coque = VGroup(
        Circle(radius=0.34, fill_color=GRIS_M, fill_opacity=1,
               stroke_color=PT, stroke_width=8).move_to(c + UP * 1.02),
        Arc(radius=0.20, start_angle=PI * 0.2, angle=PI * 1.2,
            arc_center=c + UP * 1.02).set_stroke(PT, 5))

    orE = Ellipse(width=0.20, height=0.30, fill_color=PELE_M, fill_opacity=1,
                  stroke_color=PT, stroke_width=7).move_to(c + LEFT * 0.92 + DOWN * 0.10)
    orD = Ellipse(width=0.20, height=0.30, fill_color=PELE_M, fill_opacity=1,
                  stroke_color=PT, stroke_width=7).move_to(c + RIGHT * 0.92 + DOWN * 0.10)
    brincoE = Dot(orE.get_bottom() + DOWN * 0.06, radius=0.07, color="#e0b33a").set_stroke(PT, 3)
    brincoD = Dot(orD.get_bottom() + DOWN * 0.06, radius=0.07, color="#e0b33a").set_stroke(PT, 3)

    # sobrancelhas ARQUEADAS pra cima = acolhedora (o oposto do V do Ranzinza)
    if humor == "conspirando":
        sobE = ArcBetweenPoints(c + LEFT * 0.54 + UP * 0.34, c + LEFT * 0.14 + UP * 0.36,
                                angle=-PI / 4).set_stroke(GRIS_M, 11)
        sobD = ArcBetweenPoints(c + RIGHT * 0.14 + UP * 0.52, c + RIGHT * 0.54 + UP * 0.44,
                                angle=-PI / 4).set_stroke(GRIS_M, 11)
    else:
        sobE = ArcBetweenPoints(c + LEFT * 0.54 + UP * 0.34, c + LEFT * 0.14 + UP * 0.38,
                                angle=-PI / 3.2).set_stroke(GRIS_M, 11)
        sobD = ArcBetweenPoints(c + RIGHT * 0.14 + UP * 0.38, c + RIGHT * 0.54 + UP * 0.34,
                                angle=-PI / 3.2).set_stroke(GRIS_M, 11)

    oe = Dot(c + LEFT * 0.32 + UP * 0.06, radius=0.10, color=PT)
    od = Dot(c + RIGHT * 0.32 + UP * 0.06, radius=0.10, color=PT)
    cilios = VGroup(
        Line(c + LEFT * 0.44 + UP * 0.18, c + LEFT * 0.38 + UP * 0.24, stroke_color=PT, stroke_width=4),
        Line(c + RIGHT * 0.38 + UP * 0.24, c + RIGHT * 0.44 + UP * 0.18, stroke_color=PT, stroke_width=4))
    # bochechas rosadas — o detalhe que a faz ler como "simpática" na miniatura
    bochE = Ellipse(width=0.34, height=0.22, fill_color="#f0a9a0", fill_opacity=0.75,
                    stroke_width=0).move_to(c + LEFT * 0.50 + DOWN * 0.30)
    bochD = Ellipse(width=0.34, height=0.22, fill_color="#f0a9a0", fill_opacity=0.75,
                    stroke_width=0).move_to(c + RIGHT * 0.50 + DOWN * 0.30)

    # óculos REDONDOS com CORRENTINHA descendo dos dois lados
    lenteE = Circle(radius=0.28, stroke_color=PT, stroke_width=7,
                    fill_opacity=0).move_to(c + LEFT * 0.32 + UP * 0.04)
    lenteD = Circle(radius=0.28, stroke_color=PT, stroke_width=7,
                    fill_opacity=0).move_to(c + RIGHT * 0.32 + UP * 0.04)
    ponte = Line(c + LEFT * 0.04 + UP * 0.04, c + RIGHT * 0.04 + UP * 0.04,
                 stroke_color=PT, stroke_width=6)

    def _corrente(x_sinal):
        pts = [c + x_sinal * 0.60 + UP * 0.04]
        for k in range(1, 5):
            pts.append(c + x_sinal * (0.78 + 0.05 * (k % 2)) + DOWN * (0.10 * k))
        cur = VMobject(stroke_color="#c9a227", stroke_width=4)
        cur.set_points_smoothly(pts)
        return cur
    oculos = VGroup(lenteE, lenteD, ponte, _corrente(LEFT), _corrente(RIGHT))

    nariz = Ellipse(width=0.20, height=0.24, fill_color="#eec3a4", fill_opacity=1,
                    stroke_color=PT, stroke_width=5).move_to(c + DOWN * 0.20)

    # BOCA sorrindo — é esta que vai pro lip sync
    if humor == "conspirando":
        boca = ArcBetweenPoints(c + DOWN * 0.56 + LEFT * 0.24, c + DOWN * 0.48 + RIGHT * 0.24,
                                angle=PI / 3.5).set_stroke(PT, 8)
    else:
        boca = ArcBetweenPoints(c + DOWN * 0.52 + LEFT * 0.26, c + DOWN * 0.52 + RIGHT * 0.26,
                                angle=PI / 2.6).set_stroke(PT, 8)

    # --- corpo ---
    pesc = Line(cab.get_bottom(), cab.get_bottom() + DOWN * 0.20, stroke_color=PT, stroke_width=15)
    t = pesc.get_end()

    blusa = Polygon(t + LEFT * 0.60, t + RIGHT * 0.60,
                    t + DOWN * 1.60 + RIGHT * 0.90, t + DOWN * 1.60 + LEFT * 0.90,
                    fill_color=BLUSA_M, fill_opacity=1, stroke_color=PT, stroke_width=10)
    # avental por cima, mais estreito, com alça no pescoço
    av = Polygon(t + DOWN * 0.30 + LEFT * 0.38, t + DOWN * 0.30 + RIGHT * 0.38,
                 t + DOWN * 1.60 + RIGHT * 0.66, t + DOWN * 1.60 + LEFT * 0.66,
                 fill_color=AVENTAL, fill_opacity=1, stroke_color=PT, stroke_width=8)
    alca = VGroup(
        Line(t + DOWN * 0.30 + LEFT * 0.30, t + LEFT * 0.16, stroke_color=AVENTAL_ESC, stroke_width=9),
        Line(t + DOWN * 0.30 + RIGHT * 0.30, t + RIGHT * 0.16, stroke_color=AVENTAL_ESC, stroke_width=9))
    # florzinhas do avental
    flores = VGroup()
    rng = np.random.default_rng(9)
    for (dx, dy) in [(-0.30, 0.62), (0.10, 0.52), (0.36, 0.86), (-0.10, 1.02),
                     (-0.42, 1.20), (0.30, 1.30)]:
        p = t + RIGHT * dx + DOWN * (0.30 + dy)
        petalas = VGroup(*[Dot(p + np.array([np.cos(a) * 0.075, np.sin(a) * 0.075, 0]),
                               radius=0.055, color="#f2f0e6") for a in np.arange(0, TAU, TAU / 5)])
        flores.add(VGroup(petalas, Dot(p, radius=0.045, color="#e2685f")))
    bolso = VGroup(
        Polygon(t + DOWN * 1.10 + LEFT * 0.34, t + DOWN * 1.10 + LEFT * 0.02,
                t + DOWN * 1.42 + LEFT * 0.02, t + DOWN * 1.42 + LEFT * 0.34,
                fill_color=AVENTAL_ESC, fill_opacity=1, stroke_color=PT, stroke_width=5))

    omb = t + DOWN * 0.25
    be = Line(omb + LEFT * 0.52, omb + DOWN * 0.86 + LEFT * 0.80, stroke_color=PT, stroke_width=15)
    bd = Line(omb + RIGHT * 0.52, omb + DOWN * 0.86 + RIGHT * 0.80, stroke_color=PT, stroke_width=15)
    maoE = Dot(be.get_end(), radius=0.13, color=PELE_M).set_stroke(PT, 5)
    maoD = Dot(bd.get_end(), radius=0.13, color=PELE_M).set_stroke(PT, 5)

    q = t + DOWN * 1.60
    saia = Polygon(q + LEFT * 0.90, q + RIGHT * 0.90,
                   q + DOWN * 0.62 + RIGHT * 1.02, q + DOWN * 0.62 + LEFT * 1.02,
                   fill_color="#6b5b8a", fill_opacity=1, stroke_color=PT, stroke_width=8)
    pe = Line(q + DOWN * 0.58 + LEFT * 0.32, q + DOWN * 1.42 + LEFT * 0.42, stroke_color=PT, stroke_width=17)
    pd = Line(q + DOWN * 0.58 + RIGHT * 0.32, q + DOWN * 1.42 + RIGHT * 0.42, stroke_color=PT, stroke_width=17)
    chE = Ellipse(width=0.42, height=0.19, fill_color="#b4674a", fill_opacity=1,
                  stroke_color=PT, stroke_width=5).move_to(pe.get_end() + DOWN * 0.04 + LEFT * 0.06)
    chD = Ellipse(width=0.42, height=0.19, fill_color="#b4674a", fill_opacity=1,
                  stroke_color=PT, stroke_width=5).move_to(pd.get_end() + DOWN * 0.04 + RIGHT * 0.06)

    grupo = VGroup(pesc, saia, pe, pd, chE, chD, blusa, av, alca, flores, bolso,
                   be, bd, maoE, maoD,
                   orE, orD, brincoE, brincoD, moldura, cab, coque,
                   bochE, bochD, nariz, oculos, sobE, sobD, oe, od, cilios, boca)
    return dict(grupo=grupo, cab=cab, oe=oe, od=od, boca=boca, oculos=oculos,
                maoE=maoE, maoD=maoD, sobE=sobE, sobD=sobD, avental=av, bracoE=be, bracoD=bd)


# =====================================================================
#  QUINTAL COM VARAL — o cenário da Dona Maria
#  O varal é a marca visual dela e as roupas balançam pra cena respirar.
#  Ele NÃO é mais assunto do roteiro (o índice de varal saiu quando ela passou
#  a dar a previsão do dia seguinte, às 18h).
# =====================================================================
CORES_ROUPA = ["#e2685f", "#7aa9c4", "#e8b04b", "#8fbf72", "#d98cb3", "#f2f0e6"]


def _peca_roupa(tipo, cor, larg=0.62):
    """Camiseta, calça ou pano de prato pendurado."""
    if tipo == "camiseta":
        corpo = Polygon([-larg / 2, 0, 0], [larg / 2, 0, 0],
                        [larg / 2, -0.78, 0], [-larg / 2, -0.78, 0],
                        fill_color=cor, fill_opacity=1, stroke_color=PT, stroke_width=5)
        mE = Polygon([-larg / 2, 0, 0], [-larg / 2 - 0.20, -0.14, 0],
                     [-larg / 2 - 0.20, -0.40, 0], [-larg / 2, -0.30, 0],
                     fill_color=cor, fill_opacity=1, stroke_color=PT, stroke_width=5)
        mD = mE.copy().flip(UP).move_to([larg / 2 + 0.10, mE.get_center()[1], 0])
        return VGroup(corpo, mE, mD)
    if tipo == "calca":
        return VGroup(
            Polygon([-larg / 2, 0, 0], [larg / 2, 0, 0], [larg / 2, -0.35, 0],
                    [-larg / 2, -0.35, 0], fill_color=cor, fill_opacity=1,
                    stroke_color=PT, stroke_width=5),
            Polygon([-larg / 2, -0.32, 0], [-0.04, -0.32, 0], [-0.06, -1.0, 0],
                    [-larg / 2, -1.0, 0], fill_color=cor, fill_opacity=1,
                    stroke_color=PT, stroke_width=5),
            Polygon([0.04, -0.32, 0], [larg / 2, -0.32, 0], [larg / 2, -1.0, 0],
                    [0.06, -1.0, 0], fill_color=cor, fill_opacity=1,
                    stroke_color=PT, stroke_width=5))
    return Polygon([-larg / 2, 0, 0], [larg / 2, 0, 0], [larg / 2, -0.62, 0],
                   [-larg / 2, -0.62, 0], fill_color=cor, fill_opacity=1,
                   stroke_color=PT, stroke_width=5)


def quintal_varal(condicao="sol", n_pecas=5):
    """Quintal com varal de roupa. Devolve dict como varanda(), mais:
        roupas -> VGroup das peças (balançam)
        corda  -> a linha do varal (não se move)
    """
    cores, _ = CEUS.get(condicao, CEUS["sol"])
    W = config.frame_width
    H = config.frame_height
    g = VGroup()
    g.add(ceu(condicao))

    raios = astro = None
    nuvens = VGroup()
    if condicao == "entardecer":
        # sol baixo, grande e sem raios: raio girando lê como meio-dia. A altura
        # (H/2 - 4.2) deixa o disco entre os morros e a faixa do painel de dados.
        astro = Circle(radius=0.85, fill_color="#ffd06a", fill_opacity=1,
                       stroke_width=0)
        g.add(astro.move_to([-W / 2 + 1.8, H / 2 - 4.2, 0]))
        nuvens.add(_nuvem(0.95, "#f7b58f", 0.85).move_to([W / 2 - 1.8, H / 2 - 2.4, 0]),
                   _nuvem(0.70, "#f9cbae", 0.80).move_to([-W / 2 + 2.4, H / 2 - 1.5, 0]))
    elif condicao == "sol":
        astro = Circle(radius=0.55, fill_color="#ffe08a", fill_opacity=1, stroke_width=0)
        raios = VGroup(*[Line(RIGHT * 0.68, RIGHT * 1.02, stroke_color="#ffe08a", stroke_width=8)
                         .rotate(a, about_point=ORIGIN) for a in np.arange(0, TAU, TAU / 12)])
        g.add(VGroup(raios, astro).move_to([-W / 2 + 1.5, H / 2 - 1.5, 0]))
        nuvens.add(_nuvem(0.75).move_to([W / 2 - 1.8, H / 2 - 2.6, 0]))
    else:
        cor_n = "#c3ccd6" if condicao == "nublado" else "#8d98a6"
        nuvens.add(_nuvem(1.1, cor_n, 0.95).move_to([-W / 2 + 2.0, H / 2 - 1.8, 0]),
                   _nuvem(0.85, cor_n, 0.95).move_to([W / 2 - 1.7, H / 2 - 2.8, 0]))
    g.add(nuvens)

    # morros ao fundo — no entardecer o verde escurece e puxa pro roxo, senão
    # o quintal fica com cor de meio-dia embaixo de um céu laranja
    entardecer = condicao == "entardecer"
    morros = ([(0.0, "#4a5a63", 1.0), (-0.5, "#3a4450", 1.25)] if entardecer
              else [(0.0, "#4a6b52", 1.0), (-0.5, "#3a5742", 1.25)])
    base_y = -H / 2 + 4.4
    for (dy, cor, esc) in morros:
        pts = [[-W / 2 - 1, base_y + dy - 2, 0]]
        xs = np.linspace(-W / 2 - 1, W / 2 + 1, 9)
        for x, a in zip(xs, [0.5, 1.5, 0.9, 1.9, 1.1, 1.7, 0.8, 1.4, 0.6]):
            pts.append([x, base_y + dy + a / esc, 0])
        pts.append([W / 2 + 1, base_y + dy - 2, 0])
        g.add(Polygon(*pts, fill_color=cor, fill_opacity=1, stroke_width=0))

    # chão de grama
    grama, grama_esc = (("#5c7f4c", "#4b6a3e") if entardecer
                        else ("#6f9b58", "#5b8248"))
    piso_y = -3.15  # plano de apoio ajustado ao enquadramento de corpo inteiro do RJ
    g.add(Rectangle(width=W + 2, height=5.4, fill_color=grama, fill_opacity=1,
                    stroke_width=0).move_to([0, piso_y - 2.7, 0]))
    g.add(Rectangle(width=W + 2, height=0.10, fill_color=grama_esc, fill_opacity=1,
                    stroke_width=0).move_to([0, piso_y, 0]))
    # tufos de grama
    rng = np.random.default_rng(13)
    for _ in range(16):
        x = rng.uniform(-W / 2, W / 2)
        y = rng.uniform(piso_y - 2.4, piso_y - 0.2)
        g.add(Line([x, y, 0], [x + rng.uniform(-0.08, 0.08), y + 0.18, 0],
                   stroke_color=grama_esc, stroke_width=5))

    # --- o varal ---
    varal_y = piso_y + 3.5
    poste_esq, poste_dir = -W / 2 + 0.9, W / 2 - 0.9
    for x in (poste_esq, poste_dir):
        g.add(Line([x, piso_y - 0.3, 0], [x, varal_y + 0.25, 0],
                   stroke_color="#7a5230", stroke_width=16))
        g.add(Line([x - 0.35, varal_y + 0.25, 0], [x + 0.35, varal_y + 0.25, 0],
                   stroke_color="#7a5230", stroke_width=12))
    # corda com barriga (catenária simplificada)
    corda = VMobject(stroke_color="#cfc6b4", stroke_width=6)
    corda.set_points_smoothly([[poste_esq, varal_y, 0], [0, varal_y - 0.35, 0],
                               [poste_dir, varal_y, 0]])
    g.add(corda)

    # roupas penduradas
    roupas = VGroup()
    tipos = ["camiseta", "calca", "pano", "camiseta", "pano", "calca"]
    xs = np.linspace(poste_esq + 0.85, poste_dir - 0.85, n_pecas)
    for k, x in enumerate(xs):
        tipo = tipos[k % len(tipos)]
        cor = CORES_ROUPA[k % len(CORES_ROUPA)]
        p = _peca_roupa(tipo, cor)
        # acompanha a barriga da corda
        y = varal_y - 0.35 * (1 - (abs(x) / max(0.001, poste_dir)) ** 2)
        p.move_to([x, y - p.height / 2, 0])
        p.topo = np.array([x, y, 0.0])
        p.fase = k * 0.9
        roupas.add(p)
        g.add(Dot([x, y, 0], radius=0.07, color="#8a6a45"))   # prendedor
    g.add(roupas)

    # bacia de roupa no chão
    bacia = VGroup(
        Ellipse(width=1.15, height=0.34, fill_color="#5aa9e6", fill_opacity=1,
                stroke_color=PT, stroke_width=6),
        Ellipse(width=0.95, height=0.22, fill_color="#f2f0e6", fill_opacity=1,
                stroke_width=0).shift(UP * 0.08))
    g.add(bacia.move_to([W / 2 - 1.6, piso_y - 1.9, 0]))

    return dict(grupo=g, raios=raios, nuvens=nuvens, astro=astro,
                piso_y=piso_y, roupas=roupas, corda=corda)


def roupas_balancando(roupas, vento=1.0, vel=1.5):
    """Balanço das peças no varal. `vento` 0..2 escala a amplitude.

    Antes o valor vinha do índice de varal (fundo ilustrando a nota). O índice
    saiu do roteiro; hoje o varal é só cenário, com uma brisa constante e suave
    pra cena não ficar congelada."""
    st = {"t": 0.0}
    for p in roupas:
        p.ang = 0.0

    def _balancar(mo, dt):
        st["t"] += dt
        for p in mo:
            alvo = 0.13 * vento * np.sin(st["t"] * vel + p.fase)
            p.rotate(alvo - p.ang, about_point=p.topo)
            p.ang = alvo
    roupas.add_updater(_balancar)


# =====================================================================
#  CTA DE SEGUIR — última batida de todo vídeo
# =====================================================================
def cta_seguir(handle="@previsaorj", chamada="TEU BAIRRO NA DM",
               sub="manda o nome e eu respondo a previsão daí"):
    """Cartaz de "siga o perfil" pro fim do vídeo.

    Fica no CENTRO da tela, não na faixa do topo: é a última coisa que a pessoa
    vê antes do loop reiniciar, e o topo do quadro é justamente onde o dedo dela
    já está indo pra deslizar. Também traz o @ escrito por extenso — quem chegou
    por compartilhamento muitas vezes não viu de qual perfil é o vídeo.
    """
    l = larg_segura()

    # pílula "+ SEGUIR" imitando o botão do app, pra leitura instantânea
    txt_botao = Text(chamada, font=FONTE, weight=BOLD, font_size=44, color=WHITE)
    pilula = RoundedRectangle(width=txt_botao.width + 1.0,
                              height=txt_botao.height + 0.5,
                              corner_radius=0.22, fill_color="#1877f2",
                              fill_opacity=1, stroke_color=WHITE, stroke_width=4)
    botao = VGroup(pilula, txt_botao)
    txt_botao.move_to(pilula)

    arroba = Text(handle, font=FONTE, weight=BOLD, font_size=36, color=AMAR)
    # A linha de baixo explica o que fazer. Virou parâmetro em 2026-08-22, com
    # a troca do CTA de seguir pelo CTA do bairro: o cartaz precisa dizer o que
    # acontece depois da mensagem, senão o pedido fica solto.
    sub = Text(sub, font=FONTE, weight=BOLD, font_size=26, color="#d8d4cd")

    miolo = VGroup(botao, arroba, sub).arrange(DOWN, buff=0.26)
    if miolo.width > l - 0.7:
        miolo.scale((l - 0.7) / miolo.width)

    band = RoundedRectangle(width=l, height=miolo.height + 0.85, corner_radius=0.3,
                            fill_color=BLACK, fill_opacity=0.82,
                            stroke_color=WHITE, stroke_width=5)
    miolo.move_to(band)
    return VGroup(band, miolo)



def conectar_bracos(v):
    """Os braços acompanham as mãos nos gestos e na respiração."""
    for side in ('E', 'D'):
        arm = v['braco' + side]
        hand = v['mao' + side]
        offset = arm.get_start() - v['cab'].get_center()
        def follow(mob, dt, hand=hand, offset=offset):
            mob.put_start_and_end_on(v['cab'].get_center() + offset, hand.get_center())
        arm.add_updater(follow)
    return v

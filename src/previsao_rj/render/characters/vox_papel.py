"""
vox_papel.py — camada "colagem de papel" (estilo Vox) do Reel do @previsaorj.

O Reel continua o mesmo: mesmas batidas, mesma voz, mesmo lip sync, mesmos
cartões de dado. Esta camada só troca a DIREÇÃO DE ARTE e a finalização:

  * folha de papel escura (vetor) + grão de papel aplicado por ffmpeg no fim;
  * o cenário do apresentador vira uma "foto colada" com moldura rasgada,
    fita adesiva e retícula atrás;
  * apresentador e Nuvem RJ com borda branca de adesivo;
  * selo do topo e cartões de dado como recortes de papel, com fita;
  * cartões entram "colados", em degraus de 12 fps;
  * carimbo no alerta;
  * legenda karaokê com banda de borda rasgada;
  * cartão de CTA em colagem;
  * master de áudio por ganho FIXO medido + limitador (sem loudnorm no
    caminho do sinal) e entrega em H.264 Main / Level 4.0, 30 fps, faststart,
    com preview leve de 720p.

Desempenho: textura de papel como imagem DENTRO do Manim deixa o render muito
mais lento. O grão entra depois, sobre o vídeo mudo, com aplicar_textura().

Tudo aqui é relativo ao quadro (dims/U), que no Reel é 8.0 x 14.222.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile

import numpy as np
from manim import (VGroup, Group, Polygon, Rectangle, RoundedRectangle, Text,
                   ImageMobject, Line, Circle, config, UP, DOWN, LEFT, RIGHT,
                   ORIGIN, PI, BLACK, WHITE)
from PIL import Image, ImageDraw, ImageFilter

FONTE = "Poppins"
CACHE = os.path.join(tempfile.gettempdir(), "previsao_rj_vox_cache")

ESTILO = dict(
    fundo="#10263a",        # papel azul-noite (a cara do perfil)
    tinta="#f7f4ef",
    grao=0.11,
    escuro=True,
    amarelo="#FFD166",
    teal="#007F87",
    vermelho="#e2483c",
    azul="#5aa9e6",
    recorte="#f3ecdc",      # papel creme dos recortes
    cartao="#15344d",       # papel escuro dos cartões de dado
    fita="#d8c38a",
    sombra=0.55,
    ink="#122E43",
)


def ativo() -> bool:
    """Chave de estilo. PREVISAO_RJ_ESTILO=classico volta ao visual anterior."""
    return os.environ.get("PREVISAO_RJ_ESTILO", "vox").strip().lower() != "classico"


def _cor(nome):
    return ESTILO.get(nome, nome)


def dims():
    w = config.frame_width
    return w, w * config.pixel_height / config.pixel_width


def U():
    """Unidade relativa: 1.0 num quadro de 8 unidades de largura."""
    return min(dims()) / 8.0


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _png(chave, gerar):
    os.makedirs(CACHE, exist_ok=True)
    nome = hashlib.md5(chave.encode()).hexdigest()[:12] + ".png"
    caminho = os.path.join(CACHE, nome)
    if not os.path.exists(caminho):
        gerar().save(caminho)
    return caminho


def texto(txt, tam, cor, peso="BOLD"):
    return Text(txt, font=FONTE, weight=peso, font_size=tam, color=_cor(cor))


# =====================================================================
#  FOLHA (vetor) + GRÃO (ffmpeg)
# =====================================================================
def folha(folga=1.6, semente=3):
    W, H = dims()
    W, H = W * folga, H * folga
    rng = np.random.default_rng(semente)
    g = VGroup(Rectangle(width=W, height=H, fill_color=ESTILO["fundo"], fill_opacity=1,
                         stroke_width=0))
    u = U()
    for _ in range(6):   # vincos da folha
        x0 = rng.uniform(-W / 2, W / 2)
        dx = rng.uniform(-W * 0.3, W * 0.3)
        a, b = np.array([x0, H / 2, 0]), np.array([x0 + dx, -H / 2, 0])
        g.add(Line(a, b, stroke_color=WHITE, stroke_width=2, stroke_opacity=0.06))
        g.add(Line(a + RIGHT * 0.02 * u, b + RIGHT * 0.02 * u,
                   stroke_color=BLACK, stroke_width=2, stroke_opacity=0.10))
    return g


def textura_png(largura, altura, semente=3):
    def gerar():
        rng = np.random.default_rng(semente)
        a = (rng.random((altura, largura)) ** 6 * 255 * ESTILO["grao"] * 2.2).astype(np.uint8)
        img = Image.new("RGBA", (largura, altura), (255, 255, 255, 0))
        img.putalpha(Image.fromarray(a))
        v = Image.new("L", (largura, altura), 0)
        lado = min(largura, altura)
        ImageDraw.Draw(v).rectangle([0, 0, largura, altura], outline=70,
                                    width=int(lado * 0.07))
        v = v.filter(ImageFilter.GaussianBlur(lado * 0.08))
        borda = Image.new("RGBA", (largura, altura), (8, 14, 22, 0))
        borda.putalpha(v)
        return Image.alpha_composite(img, borda)
    return _png(f"tex-rj-{largura}x{altura}-{semente}", gerar)


def aplicar_textura(entrada, saida, crf=18):
    """Grão de papel por cima do vídeo MUDO, antes de juntar o áudio."""
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "json", str(entrada)]))["streams"][0]
    tex = textura_png(int(info["width"]), int(info["height"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(entrada), "-loop", "1", "-i", tex,
                    "-filter_complex",
                    "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-an", "-c:v", "libx264", "-crf", str(crf),
                    "-preset", "medium", str(saida)], check=True)
    return saida


# =====================================================================
#  ÁUDIO: master por ganho fixo + limitador
# =====================================================================
def medir_lufs(arquivo):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(arquivo), "-af", "ebur128",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def ganho_para(lufs_medido, alvo=-16.5, teto=18.0):
    """Ganho FIXO em dB para levar a medição ao alvo, com teto de segurança."""
    if lufs_medido is None:
        return 0.0
    return max(-teto, min(teto, alvo - lufs_medido))


def masterizar(entrada, saida, alvo=-16.5):
    """loudnorm de passe único no caminho do sinal trabalha em modo dinâmico e
    faz a voz 'respirar'/estalar. Aqui mede, aplica ganho fixo e limita."""
    g = ganho_para(medir_lufs(entrada), alvo)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(entrada), "-af",
                    f"volume={g:.2f}dB,alimiter=limit=0.89:level=disabled",
                    "-ar", "48000", "-ac", "1", str(saida)], check=True)
    return saida


# =====================================================================
#  RECORTES
# =====================================================================
def _contorno_rasgado(w, h, dente=None, passo=None, semente=1):
    u = U()
    dente = 0.06 * u if dente is None else dente
    passo = 0.12 * u if passo is None else passo
    rng = np.random.default_rng(semente)
    pts = []

    def lado(a, b):
        n = max(2, int(np.linalg.norm(b - a) / passo))
        nor = np.array([-(b - a)[1], (b - a)[0], 0.0])
        nor /= np.linalg.norm(nor)
        for i in range(n):
            pts.append(a + (b - a) * (i / n) + nor * rng.uniform(-dente, dente))
    c = [np.array([-w / 2, -h / 2, 0.0]), np.array([w / 2, -h / 2, 0.0]),
         np.array([w / 2, h / 2, 0.0]), np.array([-w / 2, h / 2, 0.0])]
    for i in range(4):
        lado(c[i], c[(i + 1) % 4])
    return pts


def recorte(w, h, cor="recorte", girar=0.0, sombra=True, semente=1, fibra=True):
    u = U()
    pts = _contorno_rasgado(w, h, semente=semente)
    g = VGroup()
    if sombra:
        g.add(Polygon(*pts, fill_color=BLACK, fill_opacity=ESTILO["sombra"], stroke_width=0)
              .shift((RIGHT * 0.07 + DOWN * 0.09) * u))
    if fibra:
        g.add(Polygon(*_contorno_rasgado(w + 0.1 * u, h + 0.1 * u, dente=0.05 * u,
                                         semente=semente + 7),
                      fill_color="#fbf8f0", fill_opacity=1, stroke_width=0))
    g.add(Polygon(*pts, fill_color=_cor(cor), fill_opacity=1, stroke_width=0))
    return g.rotate(girar)


def fita(ponto=ORIGIN, girar=0.0, w=None, h=None):
    u = U()
    w = w or 1.0 * u
    h = h or 0.30 * u
    n, d = 6, 0.045 * u
    esq = [[-w / 2 + (d if i % 2 else -d / 2), -h / 2 + h * i / n, 0] for i in range(n + 1)]
    dir_ = [[w / 2 + (d if i % 2 else -d / 2), h / 2 - h * i / n, 0] for i in range(n + 1)]
    return Polygon(*(esq + dir_), fill_color=ESTILO["fita"], fill_opacity=0.85,
                   stroke_width=0).rotate(girar).move_to(ponto)


def reticula(w, h, cor="amarelo", forma="circulo", passo=26):
    rgb = _hex_rgb(_cor(cor))

    def gerar():
        px = 700
        py = int(px * h / w)
        img = Image.new("RGBA", (px, py), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        cx, cy = px / 2, py / 2
        for j, y in enumerate(range(0, py + passo, passo)):
            for x in range(0, px + passo, passo):
                xx = x + (passo / 2 if j % 2 else 0)
                dist = np.hypot((xx - cx) / cx, (y - cy) / cy)
                if forma == "diag":
                    dist = max((xx / px + y / py) / 2, dist * 0.95)
                r = max(0.0, 1 - dist) * passo * 0.55
                if r > 1:
                    dr.ellipse([xx - r, y - r, xx + r, y + r], fill=rgb + (255,))
        return img
    im = ImageMobject(_png(f"ret-rj-{rgb}-{w:.2f}-{h:.2f}-{forma}-{passo}", gerar))
    im.stretch_to_fit_width(w).stretch_to_fit_height(h)
    return im


# =====================================================================
#  CENÁRIO DO RIO COMO FOTO COLADA
# =====================================================================
def cena_rio(w, h, tipo="urbano", y_mar=None, y_grade=None):
    """O cenário do apresentador desenhado DENTRO de uma caixa w x h.

    Mesmo desenho do fundo clássico (céu, morros, mar, piso e guarda-corpo),
    mas com coordenadas relativas à caixa — Manim não recorta vetor, então a
    'foto' é desenhada já do tamanho da moldura. `y_mar`/`y_grade` são alturas
    ABSOLUTAS (a caixa está centrada na origem), para casar com o piso do
    apresentador.
    """
    INK = ESTILO["ink"]
    x0, x1, y0, y1 = -w / 2, w / 2, -h / 2, h / 2
    y_grade = -1.95 if y_grade is None else y_grade
    y_mar = y_grade + 1.35 if y_mar is None else y_mar
    ceu = Rectangle(width=w, height=h, fill_color="#D7EBEF", fill_opacity=1, stroke_width=0)
    mar = Polygon([x0, y_mar + 0.55, 0], [x1, y_mar + 0.55, 0], [x1, y_grade, 0],
                  [x0, y_grade, 0], fill_color="#77BBC9", fill_opacity=1, stroke_width=0)
    # Morros POR CIMA do mar, descendo até perto do guarda-corpo, como no fundo
    # clássico: o mar fica só como uma faixa entre o morro e a grade.
    hb = y_mar - 0.05
    morros = Polygon([x0, hb, 0], [x0 + w * 0.21, hb + 2.1, 0], [x0 + w * 0.40, hb + 0.2, 0],
                     [x0 + w * 0.62, hb + 1.35, 0], [x0 + w * 0.87, hb + 0.1, 0],
                     [x1, hb + 0.65, 0], [x1, y_grade + 1.15, 0], [x0, y_grade + 1.15, 0],
                     fill_color="#6A9DA6", fill_opacity=1, stroke_width=0)
    piso = Polygon([x0, y_grade, 0], [x1, y_grade, 0], [x1, y0, 0], [x0, y0, 0],
                   fill_color="#E8D9B8" if tipo == "orla" else "#BBCAD0",
                   fill_opacity=1, stroke_width=0)
    grade = VGroup(Line([x0, y_grade + 0.9, 0], [x1, y_grade + 0.9, 0], color=INK, stroke_width=6),
                   *[Line([x, y_grade + 0.9, 0], [x, y_grade, 0], color=INK, stroke_width=5)
                     for x in np.linspace(x0 + w * 0.12, x1 - w * 0.12, 5)])
    sol = Circle(radius=0.42, fill_color=ESTILO["amarelo"], fill_opacity=1,
                 stroke_width=0).move_to([x0 + w * 0.2, y1 - h * 0.12, 0])
    return VGroup(ceu, sol, mar, morros, piso, grade)


def foto_colada(conteudo, w, h, semente=1, girar=0.0, fitas=True):
    """Moldura de papel rasgado com o cenário dentro. Devolve um VGroup."""
    u = U()
    borda = 0.16 * u
    moldura = recorte(w + 2 * borda, h + 2 * borda, cor="recorte", semente=semente, fibra=False)
    moldura.move_to(conteudo)
    g = VGroup(moldura, conteudo)
    if fitas:
        g.add(fita(moldura.get_corner(UP + LEFT) + (RIGHT * 0.35 + DOWN * 0.11) * u, girar=0.65),
              fita(moldura.get_corner(DOWN + RIGHT) + (LEFT * 0.35 + UP * 0.11) * u, girar=0.65))
    if girar:
        g.rotate(girar, about_point=conteudo.get_center())
    return g


# =====================================================================
#  ADESIVO (borda branca atrás do personagem)
# =====================================================================
def borda_adesivo(partes, espessura=16, sombra=True):
    u = U()
    borda = VGroup(*[m.copy() for m in partes if m is not None and len(m.get_family()) > 0])
    for m in borda.get_family():
        m.clear_updaters()
    for m in borda.get_family():
        try:
            w = m.get_stroke_width()
            if m.get_fill_opacity() > 0 or w > 0:
                m.set_stroke(color="#fbf8f0", width=w + espessura, opacity=1)
            if m.get_fill_opacity() > 0:
                m.set_fill("#fbf8f0", opacity=1)
        except Exception:
            pass
    g = VGroup(borda)
    if sombra:
        sb = borda.copy()
        for m in sb.get_family():
            try:
                if m.get_stroke_width() > 0:
                    m.set_stroke(color=BLACK, opacity=ESTILO["sombra"])
                if m.get_fill_opacity() > 0:
                    m.set_fill(BLACK, opacity=ESTILO["sombra"])
            except Exception:
                pass
        sb.shift((RIGHT * 0.07 + DOWN * 0.09) * u)
        g.add_to_back(sb)
    return g


def adesivo_apresentador(v, espessura=16):
    """Borda de adesivo do Bira/Bia. SEM braços e mãos: eles se movem nos gestos
    e uma cópia estática deixaria um 'braço fantasma' branco. A borda segue o
    grupo do apresentador (respiração e saída de cena) por diferença."""
    fora = {id(v[k]) for k in ("bracoE", "bracoD", "maoE", "maoD") if k in v}
    G = v["grupo"]
    # Só a SILHUETA: formas preenchidas. Texto (o "RJ" da camisa) e traços
    # abertos (boca, nariz, sobrancelha, gola) ficam de fora — com traço grosso
    # as quinas do glifo viram espinhos brancos fora do corpo.
    partes = [m for m in G.submobjects
              if id(m) not in fora and not isinstance(m, Text)
              and any(f.get_fill_opacity() > 0 for f in m.get_family())]
    g = borda_adesivo(partes, espessura=espessura)
    desloc = g.get_center() - G.get_center()

    def seguir(mo, dt):
        mo.shift(G.get_center() + desloc - mo.get_center())
    g.add_updater(seguir)
    return g


# =====================================================================
#  TIPOGRAFIA DE COLAGEM
# =====================================================================
def manchete(txt, cor_papel="amarelo", cor_texto="ink", tam=44, girar=0.04,
             semente=5, desalinho=True, juntar=False, largura_max=None):
    """Palavras em pedaços de papel rasgado, tortas, com desalinhamento de
    impressão. Devolve VGroup (serve na trilha temporal)."""
    rng = np.random.default_rng(semente)
    W, _ = dims()
    u = U()
    largura_max = largura_max or W * 0.8
    pecas = []
    for i, pal in enumerate([txt] if juntar else txt.split()):
        t = texto(pal, tam, cor_texto)
        papel = recorte(t.width + 0.34 * u, t.height + 0.26 * u, cor=cor_papel,
                        semente=semente + i, sombra=True)
        camadas = [papel]
        if desalinho:
            camadas.append(t.copy().set_color(ESTILO["vermelho"]).set_opacity(0.55)
                           .shift((LEFT * 0.03 + UP * 0.025) * u))
        camadas.append(t)
        pecas.append(VGroup(*camadas).rotate(rng.uniform(-girar, girar) * 2))
    linhas, atual, larg = [], [], 0.0
    for pc in pecas:
        if atual and larg + pc.width > largura_max:
            linhas.append(atual)
            atual, larg = [], 0.0
        atual.append(pc)
        larg += pc.width + 0.08 * u
    linhas.append(atual)
    g = VGroup(*[VGroup(*l).arrange(RIGHT, buff=0.08 * u) for l in linhas])
    g.arrange(DOWN, buff=0.06 * u)
    if g.width > largura_max:
        g.scale_to_fit_width(largura_max)
    return g


def carimbo(txt, cor="vermelho", tam=40, girar=0.18, sobre="cartao"):
    u = U()
    c = _cor(cor)
    t = texto(txt, tam, c)
    m1 = RoundedRectangle(width=t.width + 0.45 * u, height=t.height + 0.36 * u,
                          corner_radius=0.08 * u, stroke_color=c, stroke_width=7,
                          fill_opacity=0)
    m2 = m1.copy().scale(1.07).set_stroke(width=3)
    g = VGroup(m2, m1, t).rotate(girar)
    rng = np.random.default_rng(len(txt))
    falhas = VGroup(*[
        Line(ORIGIN, RIGHT * rng.uniform(0.08, 0.22) * u, stroke_color=_cor(sobre),
             stroke_width=rng.uniform(2, 4), stroke_opacity=0.8)
        .move_to(g.get_center() + RIGHT * rng.uniform(-g.width / 2.3, g.width / 2.3)
                 + UP * rng.uniform(-g.height / 2.5, g.height / 2.5))
        .rotate(rng.uniform(0, PI)) for _ in range(10)])
    return VGroup(g, falhas)


def marca(handle="@previsaorj"):
    """Marca do perfil como tira de papel creme."""
    return manchete(handle, cor_papel="recorte", tam=28, semente=31, juntar=True,
                    desalinho=False, girar=0.02)


def selo(nome, rotulo="HOJE EM", largura=None):
    """Selo do topo (a cidade/assunto da vez) em colagem: rótulo numa tira
    verde-água e o nome em recortes amarelos. Corpo grande de propósito: na
    grade do perfil a miniatura tem ~330 px de largura."""
    W, _ = dims()
    largura = largura or W * 0.74
    rot = manchete(rotulo.upper(), cor_papel="teal", cor_texto="tinta", tam=24,
                   semente=11, juntar=True, desalinho=False, girar=0.02)
    nom = manchete(nome.upper(), cor_papel="amarelo", tam=52, semente=17,
                   largura_max=largura)
    g = VGroup(rot, nom).arrange(DOWN, buff=0.04 * U())
    rot.align_to(nom, LEFT).shift(LEFT * 0.1 * U())
    if g.width > largura:
        g.scale_to_fit_width(largura)
    return g


def cartao_cta(chamada="TEU BAIRRO NA DM", sub="manda o nome e eu respondo a previsão daí",
               handle="@previsaorj", largura=None):
    W, _ = dims()
    u = U()
    largura = largura or W * 0.74
    m = manchete(chamada, cor_papel="amarelo", tam=46, semente=41, juntar=True)
    s = texto(sub, 26, "tinta")
    if s.width > largura:
        s.scale_to_fit_width(largura)
    arr = manchete(handle, cor_papel="recorte", tam=38, semente=43, juntar=True,
                   desalinho=False)
    miolo = VGroup(m, arr, s).arrange(DOWN, buff=0.22 * u)
    if miolo.width > largura:
        miolo.scale_to_fit_width(largura)
    papel = recorte(miolo.width + 0.7 * u, miolo.height + 0.7 * u, cor="cartao",
                    semente=45, girar=0.0)
    papel.move_to(miolo)
    return VGroup(papel, miolo, fita(papel.get_top() + DOWN * 0.04 * u, girar=0.08))


# =====================================================================
#  CARTÕES DE DADO COMO RECORTE COLADO
# =====================================================================
def _eh_cartao(m):
    return (isinstance(m, VGroup) and len(m.submobjects) >= 2
            and isinstance(m.submobjects[0], RoundedRectangle))


def _colar_cartao(card, semente, girar):
    """Troca a banda arredondada do cartão por um papel rasgado da MESMA cor.

    Banda preta/translúcida (cartão de dado) vira papel escuro; faixa colorida
    (umidade, UV, alerta) mantém a cor, porque o texto dela é escuro."""
    band = card.submobjects[0]
    cor = band.get_fill_color().to_hex()
    r, g_, b = _hex_rgb(cor)
    escura = (0.299 * r + 0.587 * g_ + 0.114 * b) < 60
    papel = recorte(band.width, band.height, cor="cartao" if escura else cor,
                    semente=semente)
    papel.move_to(band)
    band.set_fill(opacity=0).set_stroke(width=0)
    return VGroup(papel, card).rotate(girar)


def colar_painel(m, semente=1):
    """Qualquer cartão do Reel vira recorte colado com fita.

    - cartão simples (banda + miolo): a banda vira papel escuro rasgado;
    - cartão duplo (dois cartões empilhados): cada um vira um papel;
    - desenho solto (nuvem de chuva etc.): ganha um papel escuro atrás.
    """
    u = U()
    rng = np.random.default_rng(semente)
    girar = float(rng.uniform(-0.035, 0.035))
    if _eh_cartao(m):
        g = _colar_cartao(m, semente, girar)
    elif isinstance(m, VGroup) and m.submobjects and all(_eh_cartao(s) for s in m.submobjects):
        g = VGroup(*[_colar_cartao(s, semente + 3 * k, girar * (-1) ** k)
                     for k, s in enumerate(m.submobjects)])
    else:
        papel = recorte(m.width + 0.8 * u, m.height + 0.7 * u, cor="cartao", semente=semente)
        papel.move_to(m)
        g = VGroup(papel, m).rotate(girar)
    topo = g.get_top()
    g.add(fita(topo + DOWN * 0.05 * u + RIGHT * rng.uniform(-0.6, 0.6) * u,
               girar=float(rng.uniform(-0.25, 0.25))))
    return g


# =====================================================================
#  LEGENDA KARAOKÊ COM BANDA RASGADA
# =====================================================================
def legenda_karaoke_papel(txt, ini, fim, y=-4.45, fs=42, larg=None, por_bloco=3,
                          cor_base="#f7f4ef", destaque=None, banda=None):
    """Mesmo contrato da legenda clássica: [(t0, t1, mobject)] para a trilha
    temporal. Texto SEM contorno; o contraste vem da banda rasgada."""
    W, _ = dims()
    u = U()
    destaque = destaque or ESTILO["amarelo"]
    banda = banda or ESTILO["ink"]
    larg = larg or W * 0.72
    palavras = txt.split()
    if not palavras:
        return []
    pesos = [max(2, len(p)) for p in palavras]
    total = sum(pesos)
    dur = max(0.2, fim - ini)
    t_ini, acc = [], 0.0
    for p in pesos:
        t_ini.append(ini + dur * acc / total)
        acc += p
    t_ini.append(fim)
    saida = []
    for b0 in range(0, len(palavras), por_bloco):
        bloco = palavras[b0:b0 + por_bloco]
        base = VGroup(*[texto(w, fs, cor_base) for w in bloco]).arrange(RIGHT, buff=0.22)
        k_esc = min(1.0, larg / base.width)
        faixa = Polygon(*_contorno_rasgado(base.width * k_esc + 0.6 * u,
                                           base.height * k_esc + 0.45 * u,
                                           dente=0.035 * u, semente=b0 + 3),
                        fill_color=banda, fill_opacity=0.9, stroke_width=0)
        for k in range(len(bloco)):
            partes = VGroup(*[texto(w, fs, destaque if j == k else cor_base)
                              for j, w in enumerate(bloco)]).arrange(RIGHT, buff=0.22)
            partes.scale(k_esc)
            fx = faixa.copy()
            partes.move_to(fx)
            saida.append((t_ini[b0 + k], t_ini[b0 + k + 1],
                          VGroup(fx, partes).move_to([0, y, 0])))
    return saida


# =====================================================================
#  TRILHA TEMPORAL COM ENTRADA "COLADA" EM DEGRAUS DE 12 FPS
# =====================================================================
def degrau(t, dur=0.36, fps=12):
    """Progresso 0..1 quantizado em degraus de 1/fps (movimento de recorte)."""
    if t >= dur:
        return 1.0
    n = max(1, int(round(fps * dur)))
    f = np.floor(max(0.0, t) / dur * n) / n
    return float(1 - (1 - f) ** 2)


def trilha_colada(itens, dur=0.36, fps=12, escala=1.3, giro=0.16):
    """Troca mobjects pelo RELÓGIO DA CENA (frame-exato, como o lip sync).

    Na entrada, cada item chega maior e torto e assenta em
    degraus de 12 fps — o 'papel colado'. Só chama become() quando o degrau
    muda, para não pesar o render."""
    grupo = VGroup()
    st = {"t": 0.0, "i": -2, "t0": 0.0, "passo": -1}

    def upd(mo, dt):
        st["t"] += dt
        agora = st["t"]
        idx = -1
        for k, (ini, fim, _m) in enumerate(itens):
            if ini <= agora < fim:
                idx = k
                break
        if idx != st["i"]:
            st["i"], st["t0"], st["passo"] = idx, agora, -1
            if idx < 0:
                mo.become(VGroup())
                return
        if idx < 0:
            return
        d = agora - st["t0"]
        passo = min(int(d * fps), int(round(dur * fps)))
        if passo == st["passo"]:
            return
        st["passo"] = passo
        f = degrau(d, dur, fps)
        base = itens[idx][2]
        novo = base.copy()
        if f < 1.0:
            c = base.get_center()
            novo.scale(escala + (1.0 - escala) * f, about_point=c)
            novo.rotate(giro * (1.0 - f), about_point=c)
        mo.become(novo)

    grupo.add_updater(upd)
    return grupo

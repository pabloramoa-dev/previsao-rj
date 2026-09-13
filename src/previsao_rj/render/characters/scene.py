"""
piloto.py — Reel diário do @previsaorj com o Seu Ranzinza.

9:16 (1080x1920), no tempo EXATO da narração, sem slow-fit (lição #14: cena com
boca sincronizada não pode ser desacelerada).

ORIENTADO A DADOS: nada do dia de hoje está escrito aqui. A cena lê
    {TRAB}/segs.json      -> quando cada fala começa e termina (vem do Kokoro)
    {TRAB}/conteudo.json  -> batidas (tipo de painel, ação do personagem) e cenário

AS QUATRO TÉCNICAS DE RETENÇÃO:
  1. GANCHO — abre com o número mais extremo do dia estalando na tela, não com
     o velho parado dando bom-dia (a decisão de deslizar é tomada em ~1,5s).
  2. LOOP — o primeiro e o último frame são a mesma imagem limpa (sem painel,
     sem legenda), então o replay não tem emenda. Replay é sinal forte.
  3. LEGENDA KARAOKÊ no terço central, palavra por palavra — 65% assiste sem
     som, e o rodapé fica coberto pela interface do Instagram.
  4. CÂMERA — push-in nos primeiros segundos e deriva lenta depois; nunca
     totalmente parada.

E uma quinta coisa, que não é retenção e sim IDENTIFICAÇÃO: o SELO DA CIDADE da
vez, na faixa do painel, durante as primeiras batidas. Ele existe pela grade do
perfil — sem ele, dez Reels seguidos são dez miniaturas idênticas e ninguém
sabe de que cidade é cada uma. Ver `previsao_lib.selo_cidade`.

Render:
  PREVISAO_RJ_TRAB=_trab PREVISAO_RJ_LIP_JSON=_trab/lip_full.json       manim -qm --fps 30 piloto.py Piloto
"""
from manim import *
import numpy as np
import sys, os, json
AQUI = os.path.dirname(os.path.abspath(__file__))
TRAB = os.environ.get('PREVISAO_RJ_TRAB', AQUI)
sys.path.insert(0, AQUI)
from src.previsao_rj.render.characters import visual as P
from src.previsao_rj.render.characters import core as L
from src.previsao_rj.render.characters import lip as LIP
from src.previsao_rj.render.characters import rj_cast as RJ
from src.previsao_rj.render.characters import layout as LAY
config.frame_width = 8.0
config.frame_height = 14.222
config.pixel_width = 1080
config.pixel_height = 1920
SEGS = json.load(open(os.path.join(TRAB, 'segs.json')))
CONT = json.load(open(os.path.join(TRAB, 'conteudo.json')))
BATIDAS = CONT['batidas']
CENARIO = CONT.get('cenario', 'sol')
PERSONAGEM = CONT.get('personagem', 'ranzinza')
CENARIO_TIPO = CONT.get('cenario_tipo', 'varanda')
CALOR = CONT.get('calor', False)
EH_JUAREZ = PERSONAGEM == 'juarez'
COM_GUARDA_CHUVA = PERSONAGEM not in ('maria', 'juarez')
FIM = SEGS[-1]['fim']
# Geometria vertical: ver render/characters/layout.py, que e testado no CI.
TOPO_PAINEL = LAY.TOPO_PAINEL
Y_MARCA = LAY.Y_MARCA
Y_SELO = LAY.Y_SELO
Y_CENTRAL = LAY.Y_CENTRAL
Y_LEGENDA = -4.45
TETO_CENA = 3.25
LIMPO = 0.3
ABERTURA = 0.18

def janelas(acao):
    """Segundos em que uma ação do personagem deve acontecer."""
    return [(SEGS[i]['ini'], SEGS[i]['fim']) for i, b in enumerate(BATIDAS) if i < len(SEGS) and (b.get('dados') or {}).get('acao') == acao]
CORES_GANCHO = {'frio': '#7ec8f0', 'calor': '#ff8a3d', 'chuva': '#5aa9e6', 'seco': P.AMAR, 'normal': P.AMAR, 'alerta': P.VERM}

def _duplo(a, b):
    return VGroup(a.scale(0.86), b.scale(0.86)).arrange(DOWN, buff=0.25)

def _nuvem_grande():
    n = VGroup(*[Circle(radius=r, fill_color='#cfd8e0', fill_opacity=1, stroke_color=BLACK, stroke_width=5) for r in [0.42, 0.6, 0.48]])
    n[0].shift(LEFT * 0.6)
    n[2].shift(RIGHT * 0.6)
    return n

def _faixa(texto, sub=None, cor=P.AMAR, cor_txt=BLACK, largura=None):
    largura = P.LARG_SEGURA if largura is None else largura
    largura = P.SEGURA if largura is None else largura
    largura = largura if largura is not None else P.larg_segura()
    itens = [Text(texto, font=P.FONTE, weight=BOLD, font_size=44, color=cor_txt)]
    if sub:
        itens.append(Text(sub, font=P.FONTE, weight=BOLD, font_size=30, color='#4a3b00'))
    miolo = VGroup(*itens).arrange(DOWN, buff=0.1)
    if miolo.width > largura - 0.6:
        miolo.scale((largura - 0.6) / miolo.width)
    band = RoundedRectangle(width=largura, height=miolo.height + 0.55, corner_radius=0.2, fill_color=cor, fill_opacity=0.95, stroke_color=BLACK, stroke_width=4)
    miolo.move_to(band)
    return VGroup(band, miolo)

def _card_valor(rotulo, valor):
    """Card com UM número só, no mesmo estilo escuro do card_cidade.

    Existe porque card_cidade() sempre desenha um par "min° / máx°". O painel
    "amplitude" quer mostrar a variação do dia — manhã = mínima, tarde = máxima,
    um número em cada card. Chamando card_cidade(rotulo, x, x) o mesmo valor
    saía impresso duas vezes ("12° / 12°"), que é o que aparece no REEL_V22.mp4.
    """
    largura = P.larg_segura()
    nome = Text(rotulo, font=P.FONTE, weight=BOLD, font_size=42, color=WHITE)
    temp = Text(f'{int(valor)}°', font=P.FONTE, weight=BOLD, font_size=52, color=P.AMAR)
    linha = VGroup(nome, temp).arrange(RIGHT, buff=0.5)
    if linha.width > largura - 0.7:
        linha.scale((largura - 0.7) / linha.width)
    band = RoundedRectangle(width=largura, height=linha.height + 0.55, corner_radius=0.2, fill_color=BLACK, fill_opacity=0.68, stroke_color=WHITE, stroke_width=3)
    linha.move_to(band)
    return VGroup(band, linha)

def painel(tipo, d):
    if tipo == 'gancho':
        return P.numero_gigante(d['numero'], d.get('sub'), cor=CORES_GANCHO.get(d.get('cor'), P.AMAR))
    if tipo == 'cidade':
        c = d['cidade']
        return P.card_cidade(c['nome'], c['min'], c['max'], c.get('cond', 'sol'))
    if tipo == 'resumo':
        return P.card_resumo(d['cidades'], d.get('titulo', 'AS CINCO PRINCIPAIS'), altura_max=5.6, buff=0.34, fs_titulo=32)
    if tipo == 'amplitude':
        c = d['cidade']
        return _duplo(_card_valor('Manhã', c['min']), _card_valor('Tarde', c['max']))
    if tipo == 'duas_cidades':
        a, b = (d['a'], d['b'])
        return _duplo(P.card_cidade(a['nome'], a['min'], a['max']), P.card_cidade(b['nome'], b['min'], b['max']))
    if tipo == 'umidade':
        return _faixa(f"UMIDADE {d['umidade']}%", 'beba água', largura=P.larg_segura())
    if tipo == 'sem_chuva':
        xis = VGroup(Line(LEFT * 0.85 + UP * 0.85, RIGHT * 0.85 + DOWN * 0.85, stroke_color=P.VERM, stroke_width=18), Line(LEFT * 0.85 + DOWN * 0.85, RIGHT * 0.85 + UP * 0.85, stroke_color=P.VERM, stroke_width=18))
        return VGroup(_nuvem_grande(), xis)
    if tipo == 'chuva':
        c = d['cidade']
        gotas = VGroup(*[Line(ORIGIN, DOWN * 0.32, stroke_color='#5aa9e6', stroke_width=8).shift(RIGHT * x + DOWN * 0.85) for x in (-0.5, 0.0, 0.5)])
        return VGroup(_nuvem_grande(), gotas, Text(f"{c['chuva_mm']}mm", font=P.FONTE, weight=BOLD, font_size=38, color=WHITE).shift(DOWN * 1.6))
    if tipo == 'preparar':
        return _faixa(d.get('cartaz', 'AMANHÃ'), 'deixe separado hoje', cor=P.AMAR)
    if tipo == 'uv':
        u = d['uv']
        cor = '#8fbf72' if u <= 5 else '#e8b04b' if u <= 7 else P.VERM
        return _faixa(f'UV {u}', d.get('aviso', ''), cor=cor, cor_txt=BLACK if u <= 7 else WHITE)
    if tipo == 'sensacao':
        return _duplo(_card_valor('Termômetro', d['real']), _card_valor('Você sente', d['sente']))
    if tipo == 'alerta':
        return _faixa(d.get('titulo', 'AVISO'), d.get('detalhe', ''), cor=P.VERM, cor_txt=WHITE)
    if tipo == 'cta':
        return P.cta_seguir(chamada=d.get('chamada', 'TEU BAIRRO NA DM'), sub=d.get('sub', 'manda o nome e eu respondo a previsão daí'))
    if tipo == 'fecho':
        return _faixa(d.get('texto', 'SEGUE PRA PREVISÃO DE AMANHÃ'), cor=P.VERM, cor_txt=WHITE)
    return None

class Piloto(MovingCameraScene):

    def construct(self):
        if PERSONAGEM in ('bira', 'bia'):
            self.add(RJ.backdrop('orla' if PERSONAGEM == 'bia' else 'urbano'))
            mascot = RJ.nuvem().scale(.52).move_to([2.8, 2.9, 0])
            self.add(mascot)
        elif CENARIO_TIPO == 'quintal':
            cen = P.quintal_varal(CENARIO)
            P.roupas_balancando(cen['roupas'], vento=CONT.get('vento_visual', 0.7))
            self.add(cen['grupo'])
            P.animar_cenario(self, cen, CENARIO, calor=CALOR, duracao=FIM)
        else:
            cen = P.varanda(CENARIO)
            self.add(cen['grupo'])
            P.animar_cenario(self, cen, CENARIO, calor=CALOR, duracao=FIM)
        if PERSONAGEM in ('bira', 'bia'):
            v = RJ.expression(RJ.presenter(PERSONAGEM), CONT.get('expressao','atenta'))
            RJ.blink(v)
        elif PERSONAGEM == 'maria':
            v = P.dona_maria()
        else:
            v = P.ranzinza()
        G = v['grupo']
        G.scale(1.1).move_to([0, -0.55, 0])
        if COM_GUARDA_CHUVA and CENARIO in ('chuva', 'tempestade'):
            prova = P.guarda_chuva(v)
            excesso = prova.get_top()[1] - TETO_CENA
            if excesso > 0:
                G.shift(DOWN * excesso)
        sombra = Ellipse(width=1.7, height=0.18, fill_color=BLACK, fill_opacity=0.18, stroke_width=0)
        sombra.move_to([0, G.get_bottom()[1] + 0.04, 0])
        self.add(sombra, G)
        P.conectar_bracos(v)
        L.respirar(G, amp=0.045, periodo=FIM / max(1, round(FIM / 3.0)))
        v['boca'].set_stroke(opacity=0)
        LIP.anexar_lipsync(self, v['boca'], t0=0.0, escala=1.05, deslocamento=DOWN * 0.04)
        if PERSONAGEM in ('maria', 'bira', 'bia'):
            jw = janelas('apontar')
            if jw:
                P.apontar(v, jw)
        extras = P.vestir(self, v, CENARIO, janelas_frio=janelas('tremer') or None, janelas_calor=janelas('abanar') or None, janelas_beber=janelas('beber') or None, com_guarda_chuva=COM_GUARDA_CHUVA)
        self.add(P.marca_dagua().move_to([0, Y_MARCA, 0]))
        # Resumo, gancho e CTA ocupam o centro da tela. Sem tirar o apresentador,
        # o cartaz aparece em cima do rosto dele — que foi o defeito visto no
        # primeiro ensaio. Janelas vizinhas sao fundidas para ele nao voltar ao
        # quadro por meio segundo entre o gancho e o CTA.
        janelas_sozinho = LAY.juntar_janelas(
            [(SEGS[i]['ini'], SEGS[i]['fim']) for i, b in enumerate(BATIDAS)
             if i < len(SEGS) and b['tipo'] in LAY.SOZINHOS])
        if janelas_sozinho:
            juntos = [G] + [extras[k] for k in ('guarda_chuva', 'cachecol') if k in extras]
            for s_ini, s_fim in janelas_sozinho:
                P.sair_de_cena(G, juntos, s_ini, s_fim)
        P.camera_push_in(self, dur=2.0, duracao=FIM - LIMPO)
        paineis = []
        for i, b in enumerate(BATIDAS):
            if i >= len(SEGS):
                break
            ini = max(SEGS[i]['ini'], ABERTURA)
            fim = SEGS[i]['fim'] if i + 1 < len(BATIDAS) else FIM - LIMPO
            m = painel(b['tipo'], b.get('dados') or {})
            if m is None:
                continue
            if b['tipo'] in ('gancho', 'cta'):
                m.move_to([0, Y_CENTRAL, 0])
            else:
                # Ancora pela borda de cima: a altura do cartao varia de 0.7 a
                # 5.5, e centralizar fazia o cartao alto invadir a marca.
                m.shift([0, TOPO_PAINEL - m.get_top()[1], 0])
            paineis.append((ini, fim, m))
        self.add(P.trilha_temporal(paineis, pop=0.2))
        destaque = CONT.get('destaque')
        if destaque:
            fim_selo = FIM - LIMPO
            for i, b in enumerate(BATIDAS):
                if i >= len(SEGS):
                    continue
                if b['tipo'] in ('gancho', 'cta'):
                    continue  # ficam no centro: nao disputam espaco com o selo
                if painel(b['tipo'], b.get('dados') or {}) is not None:
                    fim_selo = max(SEGS[i]['ini'], ABERTURA)
                    break
            base_selo = P.selo_cidade(destaque, CONT.get('destaque_rotulo', 'HOJE EM'))
            base_selo.move_to([0, Y_SELO, 0])
            selo = base_selo.copy()
            self.add(selo)
            st_selo = {'t': 0.0, 'on': True}

            def _selo(mo, dt):
                st_selo['t'] += dt
                on = st_selo['t'] < fim_selo or st_selo['t'] >= FIM - LIMPO
                if on != st_selo['on']:
                    mo.become(base_selo.copy() if on else VGroup())
                    st_selo['on'] = on
            selo.add_updater(_selo)
        legs = []
        for i, b in enumerate(BATIDAS):
            if i >= len(SEGS) or b['tipo'] in ('gancho', 'cta', 'resumo'):
                continue
            ini = max(SEGS[i]['ini'], ABERTURA)
            fim = SEGS[i]['fim'] if i + 1 < len(BATIDAS) else FIM - LIMPO
            legs += P.legenda_karaoke(b['legenda'], ini, fim, y=Y_LEGENDA, fs=42)
        self.add(P.trilha_temporal(legs, pop=0.1))
        jn = [(SEGS[i]['ini'], SEGS[i]['fim']) for i, b in enumerate(BATIDAS) if i < len(SEGS) and (b.get('dados') or {}).get('nevoa')]
        if jn and CENARIO != 'frio':
            P.nevoa(self, janelas=jn)
        if 'bengala' not in v:
            self.wait(FIM)
            return
        beng = v['bengala']
        stb = {'t': 0.0, 'o': 0.0}
        b_ini = SEGS[min(1, len(SEGS) - 1)]['ini'] + 0.4

        def _bengala(mo, dt):
            stb['t'] += dt
            d = stb['t'] - b_ini
            novo = 0.2 * np.sin(d / 0.34 * PI) if 0 <= d < 0.34 else 0.0
            mo.shift(UP * (novo - stb['o']))
            stb['o'] = novo
        beng.add_updater(_bengala)
        self.wait(FIM)

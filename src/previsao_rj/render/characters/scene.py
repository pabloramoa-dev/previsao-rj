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
Y_PAINEL = 4.5
Y_SELO = 3.95
Y_RESUMO = 1.2
Y_LEGENDA = -2.2
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
        if CENARIO_TIPO == 'quintal':
            cen = P.quintal_varal(CENARIO)
            P.roupas_balancando(cen['roupas'], vento=CONT.get('vento_visual', 0.7))
            self.add(cen['grupo'])
            P.animar_cenario(self, cen, CENARIO, calor=CALOR, duracao=FIM)
        else:
            cen = P.varanda(CENARIO)
            self.add(cen['grupo'])
            P.animar_cenario(self, cen, CENARIO, calor=CALOR, duracao=FIM)
        if PERSONAGEM == 'maria':
            v = P.dona_maria()
        else:
            v = P.ranzinza()
        G = v['grupo']
        G.scale(1.3).move_to([0, -2.4 if PERSONAGEM == 'maria' else -1.2, 0])
        if COM_GUARDA_CHUVA and CENARIO in ('chuva', 'tempestade'):
            prova = P.guarda_chuva(v)
            excesso = prova.get_top()[1] - TETO_CENA
            if excesso > 0:
                G.shift(DOWN * excesso)
        self.add(G)
        if CONT.get('demo'):
            self.add(Text('TESTE DE PERSONAGEM • SEM PREVISÃO', font=P.FONTE, font_size=18, color=WHITE).move_to([0, -5.1, 0]))
        P.conectar_bracos(v)
        L.respirar(G, amp=0.045, periodo=FIM / max(1, round(FIM / 3.0)))
        v['boca'].set_stroke(opacity=0)
        LIP.anexar_lipsync(self, v['boca'], t0=0.0, escala=1.25, deslocamento=DOWN * 0.04)
        if PERSONAGEM == 'maria':
            jw = janelas('apontar')
            if jw:
                P.apontar(v, jw)
        extras = P.vestir(self, v, CENARIO, janelas_frio=janelas('tremer') or None, janelas_calor=janelas('abanar') or None, janelas_beber=janelas('beber') or None, com_guarda_chuva=COM_GUARDA_CHUVA)
        self.add(P.marca_dagua().move_to([0, 5.25, 0]))
        janela_resumo = [(SEGS[i]['ini'], SEGS[i]['fim']) for i, b in enumerate(BATIDAS) if i < len(SEGS) and b['tipo'] == 'resumo']
        if janela_resumo:
            r_ini, r_fim = janela_resumo[0]
            juntos = [G] + [extras[k] for k in ('guarda_chuva', 'cachecol') if k in extras]
            P.sair_de_cena(G, juntos, r_ini, r_fim)
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
                m.move_to([0, 1.2, 0])
            elif b['tipo'] == 'resumo':
                m.move_to([0, Y_RESUMO, 0])
            else:
                m.move_to([0, Y_PAINEL, 0])
            paineis.append((ini, fim, m))
        self.add(P.trilha_temporal(paineis, pop=0.2))
        destaque = CONT.get('destaque')
        if destaque:
            fim_selo = FIM - LIMPO
            for i, b in enumerate(BATIDAS):
                if i == 0 or i >= len(SEGS):
                    continue
                if b['tipo'] in ('gancho', 'cta'):
                    continue
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
            legs += P.legenda_karaoke(b['legenda'], ini, fim, y=Y_LEGENDA, fs=48)
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

# Piloto de serviço, sem publicação: usa o compositor e a voz originais.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_hf as hf
import compor as c

def beat(fala, tipo="nenhum", **dados):
    return dict(fala=fala, legenda=fala, tipo=tipo, dados=dados)

beats = [
    beat("Vai pegar a Dutra? Atenção às interdições na Serra das Araras!"),
    beat("Quinta, dia vinte e seis, sentido São Paulo, das treze às quinze horas.", "alerta", titulo="26/11 · QUINTA", detalhe="13h–15h | SENTIDO SP"),
    beat("Sábado, dia vinte e oito, os dois sentidos fecham das dezesseis às dezoito.", "alerta", titulo="28/11 · SÁBADO", detalhe="16h–18h | AMBOS OS SENTIDOS"),
    beat("Dia trinta, sentido Rio. Primeiro de dezembro, os dois sentidos.", "alerta", titulo="30/11 · RJ", detalhe="01/12 · AMBOS | 13h–15h nos dois dias"),
    beat("Dias dois, três e cinco, sentido São Paulo. Todos das treze às quinze horas, inclusive dia trinta e dia primeiro.", "alerta", titulo="02, 03 e 05/12", detalhe="13h–15h | SENTIDO SP"),
    beat("Confira a RioSP antes de viajar e compartilhe!", "cta", chamada="COMPARTILHE O AVISO", sub="Fonte: RioSP/Motiva · 19 e 24/11/2026"),
]
def demo(personagem):
    return {"forecast":{"today":{"date":"2026-11-25","locations":[]}}}, "transito_serra_araras", beats
hf.demo_batidas = demo
c.TITULOS["transito_serra_araras"] = "DUTRA: SERRA DAS ARARAS"
c.APRESENTADOR["bira"]["cargo"] = "BOLETIM DE TRÂNSITO"
c.APRESENTADOR["bira"]["kicker"] = "SERVIÇO"
def ticker(p):
    itens = "SERRA DAS ARARAS · BR-116 · PIRAÍ E PARACAMBI · FONTE RIOSP/MOTIVA · 25/11/2026 · @PREVISAORJ"
    return '<div class="tk-faixa"><div class="tk-rot">DUTRA</div><div class="tk-janela"><div id="tk-trilho">'+itens+' &#9679; '+itens+'</div></div></div>'
c.ticker = ticker
original = c.compor
def compor(p):
    return original(p).replace("PREVISÃO DAS 6H", "BOLETIM DE TRÂNSITO").replace("HOJE · 25 NOV", "25 NOV · SERVIÇO")
c.compor = compor
out=Path("output/serra_araras/REEL.mp4").resolve()
out.parent.mkdir(parents=True,exist_ok=True)
p,b,s,w=hf.preparar("bira",out)
hf.renderizar(out,p)
hf.entregar("bira",out,p,b,s,w)
(out.parent/"LEGENDA.txt").write_text("Atenção, motoristas! Interdições na Serra das Araras: 26/11, 13h–15h SP; 28/11, 16h–18h ambos; 30/11, 13h–15h RJ; 01/12, 13h–15h ambos; 02, 03 e 05/12, 13h–15h SP. Fonte: RioSP/Motiva, comunicados de 19 e 24/11/2026. Programação sujeita a alterações. Consulte os canais oficiais antes de viajar. @previsaorj",encoding="utf-8")

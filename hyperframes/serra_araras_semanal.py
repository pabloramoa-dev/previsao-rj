"""Consulta semanal oficial e render do boletim de trânsito. Falha fechada."""
import datetime as dt, hashlib, json, os, re, sys, unicodedata
from pathlib import Path
from urllib.parse import urljoin,urlparse
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
BASE="https://rodovias.motiva.com.br"
LIST=BASE+"/riosp/noticias/"
TZ=ZoneInfo("America/Sao_Paulo")
NOW=dt.datetime.now(TZ)
TODAY=NOW.date()
OUT=Path(os.environ.get("OUT_DIR","output/serra_araras")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
CHANNEL=os.environ.get("EXPECTED_IG_USERNAME","previsaorj")
def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD",s.casefold()) if not unicodedata.combining(c))
def official(u):
    p=urlparse(u)
    return p.scheme=="https" and p.netloc=="rodovias.motiva.com.br" and re.match(r"/riosp/noticias/20\d\d/",p.path)
def get(u):
    r=requests.get(u,timeout=35,headers={"User-Agent":"Mozilla/5.0 (compatible; BoletimDeTransito/1.0)"})
    r.raise_for_status()
    if not official(r.url): raise ValueError("Redirecionamento fora da fonte oficial")
    return BeautifulSoup(r.text,"html.parser")
def discover():
    links=set()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page()
        for url in [LIST,BASE+"/riosp/busca-de-noticias/",BASE+"/riosp/"]:
            try:
                page.goto(url,wait_until="domcontentloaded",timeout=45000)
                page.wait_for_timeout(3500)
                search=page.get_by_placeholder(re.compile("Buscar em noticias",re.I))
                if search.count():
                    search.first.fill("Serra das Araras")
                    search.first.press("Enter")
                    page.wait_for_timeout(4500)
                for _ in range(3):
                    for a in page.locator("a[href]").all():
                        href=urljoin(page.url,a.get_attribute("href") or "")
                        if official(href) and ("serra-das-araras" in href or "serra-araras" in href):
                            links.add(href.split("?")[0])
                    more=page.get_by_text(re.compile("most[ra]+ mais notícias",re.I))
                    if not more.count():break
                    try:more.first.click(timeout=1500);page.wait_for_timeout(1500)
                    except Exception:break
            except Exception as e: print("Falha de descoberta",type(e).__name__)
        browser.close()
    # Descoberta alternativa, sem confiar em conteúdo de terceiros.
    if not links:
        try:
            s=BeautifulSoup(requests.get("https://www.bing.com/search",params={"q":"site:rodovias.motiva.com.br/riosp/noticias/ Serra das Araras interdições","format":"rss"},timeout=20).text,"xml")
            links.update(x.get_text(strip=True) for x in s.select("item > link") if official(x.get_text(strip=True)))
        except Exception: pass
    return sorted(links)
def collect():
    found=[]; unresolved=[]; evidence=[]
    for u in discover()[:40]:
        try:
            s=get(u); title=s.h1.get_text(" ",strip=True) if s.h1 else ""
            t=s.get_text(" ",strip=True); n=norm(t); nt=norm(title)
            if "serra das araras" not in nt:continue
            m=re.search(r"Escrito por.{0,120}?em\s+(\d{2}/\d{2}/\d{4})",t,re.I)
            if not m:continue
            pub=dt.datetime.strptime(m[1],"%d/%m/%Y").date()
            if not TODAY-dt.timedelta(days=10)<=pub<=TODAY:continue
            if not re.search(r"interdi|desmont|detona|bloque|fechamento|vigas|manutenc",nt):continue
            evidence.append({"url":u,"title":title,"date":str(pub)})
            # Datas e horários explícitos; não inferir sentido em notícia excepcional.
            default_sp=("desmont" in nt or "detona" in nt) and "pista sul (sentido sao paulo)" in n and bool(re.search(r"sentido rio de janeiro.{0,55}(normalmente|normal)",n))
            if re.search(r"cancelad|suspens|sem interdi",n):
                unresolved.append(u);continue
            rows=[]
            candidates=[x.get_text(" ",strip=True) for x in s.select("li, tr, p")]
            if default_sp:
                candidates += re.findall(r"\(\d{1,2}/\d{1,2}(?:/\d{4})?\)\s*[:,]?\s*das\s+\d{1,2}h\s+[àa]s\s+\d{1,2}h\b",t,re.I)
            for line in candidates:
                q=norm(line)
                if len(q)>400:continue
                dates=re.findall(r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/\d{4})?(?!\d)",q)
                hours=re.findall(r"(?<!\d)(\d{1,2})h\s*(?:as|a|[-–])\s*(\d{1,2})h(?!\d)",q)
                if len(dates)!=1 or len(hours)!=1:continue
                if re.search(r"ambos os sentidos|dois sentidos|nos dois sentidos|pistas norte e sul",q):sentido="Ambos os sentidos"
                elif re.search(r"sentido (sao paulo|sp)\b|pista sul",q):sentido="São Paulo"
                elif re.search(r"sentido (rio de janeiro|rio|rj)\b|pista norte",q):sentido="Rio de Janeiro"
                elif default_sp:sentido="São Paulo"
                else:continue
                d,mo=dates[0];a,b=map(int,hours[0])
                year=pub.year+(int(mo)<pub.month and pub.month==12)
                day=dt.date(year,int(mo),int(d))
                if not 0<=a<b<=23:raise ValueError("Horário inválido")
                if TODAY<=day<=TODAY+dt.timedelta(days=6) and dt.datetime.combine(day,dt.time(a),TZ)>NOW:
                    rows.append((str(day),a,b,sentido))
            if rows:found.append((pub,u,sorted(set(rows))))
            elif not default_sp or not re.search(r"\(\d{1,2}/\d{1,2}\)",t):unresolved.append(u)
        except Exception as e:
            print("Falha de leitura",u,type(e).__name__);unresolved.append(u)
    if unresolved:raise RuntimeError("Comunicado recente não interpretável; revisão necessária: "+str(unresolved))
    if not found:raise RuntimeError("Sem cronograma oficial vigente e verificável")
    found.sort(reverse=True)
    pub,url,rows=found[0]
    if any(other!=rows for _,_,other in found[1:]):raise RuntimeError("Comunicados divergentes; revisar antes de publicar")
    report={"rows":rows,"source":url,"published":str(pub),"checked":NOW.isoformat(),"evidence":evidence}
    (OUT/"consulta.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report
def capa_transito(report):
    """Capa independente, com texto na área central segura da grade."""
    from PIL import Image, ImageDraw, ImageFont
    im=Image.new("RGB",(1080,1920),"#10202D")
    draw=ImageDraw.Draw(im)
    def center(s,y,size,color,bold=True):
        name="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        f=ImageFont.truetype(name,size)
        while draw.textlength(s,font=f)>900 and size>20:
            size-=2; f=ImageFont.truetype(name,size)
        draw.text((540,y),s,font=f,fill=color,anchor="mt")
    for y in (0,1740):
        draw.rectangle((0,y,1080,y+180),fill="#F7C744")
        for x in range(-180,1260,180):
            draw.polygon([(x,y),(x+70,y),(x-110,y+180),(x-180,y+180)],fill="#24313A")
    draw.rounded_rectangle((60,410,1020,1510),radius=48,fill="#142C3C",outline="#426477",width=4)
    draw.rounded_rectangle((196,472,884,566),radius=24,fill="#F7C744")
    center("BOLETIM DE TRÂNSITO",492,43,"#14232D")
    center("SERRA DAS",628,108,"#FFFFFF")
    center("ARARAS",748,144,"#FFFFFF")
    center("VIA DUTRA  •  BR-116",935,49,"#F7C744")
    draw.line((155,1020,925,1020),fill="#426477",width=3)
    center("INTERDIÇÕES",1060,76,"#FFFFFF")
    center("DA SEMANA",1148,76,"#FFFFFF")
    days=sorted(dt.date.fromisoformat(row[0]) for row in report["rows"])
    period=days[0].strftime("%d/%m")
    if days[-1]!=days[0]:
        period+=" A "+days[-1].strftime("%d/%m")
    center(period,1265,57,"#F7C744")
    center("@"+CHANNEL.upper(),1400,35,"#D6E5EC")
    center("FONTE: RIOSP / MOTIVA",1580,32,"#D6E5EC",False)
    path=OUT/"CAPA.jpg"
    im.save(path,"JPEG",quality=95,subsampling=0,optimize=True)
    if path.stat().st_size<10000:
        raise RuntimeError("Capa de trânsito inválida")
    print("Capa de grade exclusiva: Serra das Araras")

def render(report):
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import gerar_hf as hf
    import compor as c
    def beat(fala,tipo="nenhum",**dados):return dict(fala=fala,legenda=fala,tipo=tipo,dados=dados)
    beats=[beat("Vai pegar a Dutra? Confira as interdições na Serra das Araras.")]
    for iso,a,b,sentido in report["rows"]:
        d=dt.date.fromisoformat(iso); data=d.strftime("%d/%m")
        beats.append(beat(f"Dia {d.day} do mês {d.month}, das {a} às {b} horas, sentido {sentido}.","alerta",titulo=data+" · "+hf.DIAS[d.weekday()],detalhe=f"{a}h–{b}h | {sentido.upper()}"))
    beats.append(beat("Consulte a RioSP antes de viajar. Envie para quem vai dirigir na Via Dutra nessa semana!","cta",chamada="ENVIE PARA QUEM VAI DIRIGIR NA VIA DUTRA NESSA SEMANA",sub="Fonte: RioSP/Motiva · "+report["published"]))
    hf.demo_batidas=lambda p:({"forecast":{"today":{"date":str(TODAY),"locations":[]}}},"transito_serra_araras",beats)
    c.TITULOS["transito_serra_araras"]="DUTRA: SERRA DAS ARARAS"
    c.APRESENTADOR["bira"]["cargo"]="BOLETIM DE TRÂNSITO"
    c.APRESENTADOR["bira"]["kicker"]="SERVIÇO"
    def ticker(p):
        itens="SERRA DAS ARARAS · BR-116 · FONTE RIOSP/MOTIVA · @"+CHANNEL.upper()
        return '<div class="tk-faixa"><div class="tk-rot">DUTRA</div><div class="tk-janela"><div id="tk-trilho">'+itens+' &#9679; '+itens+'</div></div></div>'
    c.ticker=ticker
    original=c.compor
    brand="PREVISÃO SUL FLUMINENSE" if CHANNEL=="previsaosulflu" else "PREVISÃO RJ"
    c.compor=lambda p:original(p).replace("PREVISÃO DAS 8H","BOLETIM DE TRÂNSITO").replace("PREVISÃO DAS 6H","BOLETIM DE TRÂNSITO").replace("PREVISÃO RJ",brand).replace("@previsaorj","@"+CHANNEL).replace("@PREVISAORJ","@"+CHANNEL.upper())
    if CHANNEL=="previsaosulflu":
        f=Path(hf.AQUI)/"compositions/instagram-follow.html"
        f.write_text(f.read_text().replace("previsaorj",CHANNEL).replace("PREVISAORJ",CHANNEL.upper()).replace("Previsão RJ","Previsão Sul Fluminense"))
    out=OUT/"REEL.mp4"
    p,b,s,w=hf.preparar("bira",out)
    hf.renderizar(out,p);hf.entregar("bira",out,p,b,s,w)
    capa_transito(report)
    caption="Interdições programadas na Serra das Araras – Via Dutra.\n"+"\n".join(f"{dt.date.fromisoformat(d):%d/%m}: {a}h–{b}h, sentido {s}" for d,a,b,s in report["rows"])+"\nFonte: "+report["source"]+"\nSujeito a alterações. Consulte a RioSP antes de viajar. Envie para quem vai dirigir na Via Dutra nessa semana! @"+CHANNEL
    (OUT/"LEGENDA.txt").write_text(caption)
    (OUT/"marker.txt").write_text("#SerraAraras"+hashlib.sha256(json.dumps(report["rows"]).encode()).hexdigest()[:12])
if __name__=="__main__":
    render(collect())

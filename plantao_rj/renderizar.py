"""Render vertical autônomo do plantão: Pillow + FFmpeg + Kokoro.
Não utiliza HyperFrames, motores ou roteiros dos Reels anteriores."""
import json
import math
import re
import subprocess
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image,ImageDraw,ImageFont

OUT=Path("output/plantao_rj")
CACHE=Path.home()/".cache"/"plantao_rj"
MODEL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
SIZE=(1080,1920)
COLOR={"ciclone":(255,186,70),"granizo":(165,202,255),
       "temporal":(255,180,90),"chuva":(96,208,252),"vento":(125,228,194)}
TITULOS={"ciclone":"AVISO DE CICLONE","granizo":"RISCO DE GRANIZO",
         "temporal":"RISCO DE TEMPORAL","chuva":"CHUVA INTENSA",
         "vento":"VENTOS FORTES"}
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TZ=ZoneInfo("America/Sao_Paulo")

def fresh(rel):
    agora=datetime.now(TZ);emitido=datetime.fromisoformat(rel["emitido_em"])
    if not timedelta(0)<=agora-emitido<=timedelta(hours=2):
        raise ValueError("Consulta antiga")
    if not rel["publicar"] or not rel["eventos"]:
        raise ValueError("Sem evidência meteorológica")
    e=rel["eventos"][0]
    if datetime.fromisoformat(e["fim"])<=agora:raise ValueError("Aviso expirado")
    if e["tipo"]=="ciclone" and e.get("fonte")!="INMET":
        raise ValueError("Ciclone só com aviso oficial")
    return e

def roteiro(rel,e):
    ini=datetime.fromisoformat(e["inicio"]).astimezone(TZ)
    fim=datetime.fromisoformat(e["fim"]).astimezone(TZ)
    tipo=e["tipo"];local=e["local"]; titulo=TITULOS[tipo]
    base=f"de {ini:%d/%m às %H:%M} até {fim:%d/%m às %H:%M}"
    if e.get("fonte")=="INMET":
        abertura=f"Atenção, Rio de Janeiro! O INMET divulgou aviso de {e['evento'].lower()} para {local}."
        detalhe=f"O aviso é válido {base}. É um risco previsto, não uma ocorrência confirmada em todos os bairros."
        fonte="AVISO OFICIAL INMET"
        url=e["url"]
    else:
        abertura=f"Atenção, região do Rio! Há previsão de {titulo.lower()} em {local}."
        if tipo=="chuva":conteudo=f"Os modelos apontam pelo menos {e['valor']:g} {e['unidade']}."
        elif tipo=="vento":conteudo=f"Os modelos apontam rajadas de até pelo menos {e['valor']:g} quilômetros por hora."
        else:conteudo="Os dois modelos meteorológicos indicam possibilidade desse fenômeno."
        detalhe=f"{conteudo} Janela prevista: {base}. Isso não é certeza."
        fonte="PREVISÃO ICON + GFS"
        url="https://open-meteo.com/"
    final="Acompanhe a Defesa Civil. Evite áreas de risco, árvores e vias alagadas. Compartilhe este aviso."
    linhas=[abertura,detalhe,final]
    legenda=("PLANTÃO METEOROLÓGICO — PREVISÃO RJ\\n\\n"+
             "\\n\\n".join(linhas)+f"\\n\\nFonte: {fonte} — {url}"+
             f"\\nConsulta: {rel['emitido_em']}\\n@previsaorj #AlertaMeteorologico")
    return linhas,legenda,fonte

def reduzir(d,texto,largura,max_font=88,min_font=35):
    for size in range(max_font,min_font-1,-2):
        f=ImageFont.truetype(FONT,size)
        if d.textbbox((0,0),texto,font=f)[2]<=largura:return f
    return ImageFont.truetype(FONT,min_font)

def wrap(d,txt,font,width):
    parts=[];line=""
    for word in txt.split():
        next_line=(line+" "+word).strip()
        if d.textbbox((0,0),next_line,font=font)[2]>width and line:
            parts.append(line);line=word
        else:line=next_line
    if line:parts.append(line)
    return parts

def imagem(tipo,titulo,local,fonte,periodo,texto,path):
    img=Image.new("RGB",SIZE,(8,22,42));d=ImageDraw.Draw(img)
    ac=COLOR[tipo]
    d.rectangle((0,0,1080,24),fill=ac)
    d.text((76,130),"PREVISÃO RJ",font=ImageFont.truetype(FONT,62),fill="white")
    d.text((76,220),"PLANTÃO METEOROLÓGICO",font=ImageFont.truetype(REG,37),fill=(185,210,230))
    d.rounded_rectangle((65,375,1015,1510),radius=48,fill=(20,42,69),outline=(61,86,115),width=4)
    tf=reduzir(d,titulo,820,75)
    for i,line in enumerate(wrap(d,titulo,tf,820)):
        d.text((110,490+i*98),line,font=tf,fill=ac)
    d.text((110,740),"REGIÃO",font=ImageFont.truetype(REG,34),fill=(171,195,213))
    lf=reduzir(d,local.upper(),830,64)
    for i,line in enumerate(wrap(d,local.upper(),lf,830)):
        d.text((110,810+i*80),line,font=lf,fill="white")
    d.line((110,1010,960,1010),fill=(74,103,131),width=3)
    bf=ImageFont.truetype(REG,43)
    for i,line in enumerate(wrap(d,texto,bf,830)[:6]):
        d.text((110,1050+i*65),line,font=bf,fill=(236,241,247))
    d.rounded_rectangle((75,1570,1005,1685),radius=26,fill=(34,72,101))
    ff=reduzir(d,fonte,830,43)
    d.text((110,1605),fonte,font=ff,fill="white")
    d.text((80,1740),periodo,font=reduzir(d,periodo,920,36),fill=ac)
    img.save(path,quality=94)

def garantir_modelos():
    CACHE.mkdir(parents=True,exist_ok=True)
    for name in ("kokoro-v1.0.onnx","voices-v1.0.bin"):
        p=CACHE/name
        if not p.exists() or p.stat().st_size<1000000:
            subprocess.run(["curl","-fsSL","--retry","3","--output",str(p),MODEL+name],check=True)
            if p.stat().st_size<1000000:raise RuntimeError("Modelo Kokoro incompleto")
    return str(CACHE/"kokoro-v1.0.onnx"),str(CACHE/"voices-v1.0.bin")

def sintetizar(linhas):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    model,voices=garantir_modelos()
    k=Kokoro(model,voices)
    full=[];dur=[]
    for i,txt in enumerate(linhas):
        txt=re.sub(r"\\b(\\d{1,2}):(\\d{2})\\b",r"\\1 horas e \\2 minutos",txt)
        samples,sr=k.create(txt,voice="pf_dora",speed=1.01,lang="pt-br")
        wave=np.asarray(samples,dtype=np.float32)
        if sr!=24000:
            dest=24000
            wave=np.interp(np.linspace(0,len(wave)-1,int(len(wave)*dest/sr)),
                           np.arange(len(wave)),wave).astype(np.float32)
            sr=dest
        pad=np.zeros(int(sr*0.45),dtype=np.float32)
        full.extend([wave,pad]);dur.append((len(wave)+len(pad))/sr)
    sf.write(OUT/"narracao.wav",np.concatenate(full),24000)
    return dur

def main():
    rel=json.loads((OUT/"consulta.json").read_text())
    e=fresh(rel)
    linhas,legenda,fonte=roteiro(rel,e)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"LEGENDA.txt").write_text(legenda,encoding="utf-8")
    dur=sintetizar(linhas)
    ini=datetime.fromisoformat(e["inicio"]).astimezone(TZ)
    fim=datetime.fromisoformat(e["fim"]).astimezone(TZ)
    periodo=f"VALIDADE: {ini:%d/%m %H:%M} — {fim:%d/%m %H:%M}"
    imgs=[]
    mensagens=[
        "Confira o risco meteorológico previsto na sua região.",
        "Dados verificados e janela de validade do alerta.",
        "Defesa Civil 199 | Bombeiros 193"]
    for i in range(3):
        path=OUT/f"cena_{i}.jpg"
        imagem(e["tipo"],TITULOS[e["tipo"]],e["local"],fonte,periodo,mensagens[i],path)
        imgs.append(path)
    (OUT/"CAPA.jpg").write_bytes(imgs[0].read_bytes())
    concat=OUT/"cenas.txt"
    with concat.open("w") as f:
        for p,d in zip(imgs,dur):
            f.write("file '"+p.name+"'\\n")
            f.write("duration "+str(round(d,3))+"\\n")
        f.write("file '"+imgs[-1].name+"'\\n")
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0",
        "-i",str(concat),"-i",str(OUT/"narracao.wav"),"-shortest",
        "-vf","fps=30,format=yuv420p","-c:v","libx264","-profile:v","main",
        "-level","4.0","-preset","medium","-crf","21","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-movflags","+faststart",
        str(OUT/"ALERTA.mp4")],check=True)
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams",
      "-show_format","-of","json",str(OUT/"ALERTA.mp4")]))
    video=[s for s in meta["streams"] if s["codec_type"]=="video"]
    audio=[s for s in meta["streams"] if s["codec_type"]=="audio"]
    if len(video)!=1 or not audio or (video[0]["width"],video[0]["height"])!=SIZE:
        raise RuntimeError("QA: vídeo incompleto")
    if not 8<=float(meta["format"]["duration"])<=180:
        raise RuntimeError("QA: duração inesperada")
    print("Render independente:",OUT/"ALERTA.mp4")

if __name__=="__main__":
    main()

from __future__ import annotations
import argparse, json, math, subprocess, tempfile, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.previsao_rj.editorial.script import build_script

W,H=540,960
FPS=30
DURATION=18.0
FONT='/usr/share/fonts/truetype/lato/Lato-Bold.ttf'
FONT_R='/usr/share/fonts/truetype/lato/Lato-Regular.ttf'

def fnt(size,bold=True): return ImageFont.truetype(FONT if bold else FONT_R,size)

def centered(draw, text, y, font, fill, maxw=470):
    # simple wrap by words
    words=text.split(); lines=[]; line=''
    for word in words:
        cand=(line+' '+word).strip()
        if draw.textbbox((0,0),cand,font=font)[2] <= maxw: line=cand
        else:
            if line: lines.append(line)
            line=word
    if line: lines.append(line)
    yy=y
    for line in lines:
        box=draw.textbbox((0,0),line,font=font); x=(W-(box[2]-box[0]))//2
        draw.text((x,yy),line,font=font,fill=fill)
        yy += (box[3]-box[1])+7
    return yy

def draw_bira(d, t):
    # personagem vetorial determinístico, família própria do RJ.
    bob=2*math.sin(t*2.2)
    x,y=118,650+bob
    # corpo
    d.rounded_rectangle((62,y+85,180,y+235),28,fill='#F5C84B',outline='#0B1F33',width=7)
    # cabeça
    d.ellipse((64,y,176,y+120),fill='#E9B98B',outline='#0B1F33',width=7)
    # cabelo
    d.pieslice((68,y-10,172,y+75),180,360,fill='#17324D')
    # orelha
    d.ellipse((54,y+48,75,y+77),fill='#E9B98B',outline='#0B1F33',width=4)
    d.ellipse((165,y+48,186,y+77),fill='#E9B98B',outline='#0B1F33',width=4)
    # olhos
    d.ellipse((90,y+47,100,y+58),fill='#0B1F33'); d.ellipse((139,y+47,149,y+58),fill='#0B1F33')
    # sobrancelhas
    d.line((87,y+39,103,y+36),fill='#0B1F33',width=5); d.line((136,y+36,152,y+39),fill='#0B1F33',width=5)
    # boca alterna suavemente
    mouth=7+3*abs(math.sin(t*5.5))
    d.arc((105,y+73,136,y+73+mouth),0,180,fill='#0B1F33',width=4)
    # braços / gesto
    handx=195+12*math.sin(t*1.7)
    d.line((170,y+120,handx,y+92),fill='#0B1F33',width=9)
    d.ellipse((handx-7,y+84,handx+8,y+99),fill='#E9B98B',outline='#0B1F33',width=3)

def draw_cloud(d,t,x,y,scale=1.0,face=False):
    off=6*math.sin(t*.8)
    x+=off
    col='#EAF4FB'
    for cx,cy,r in [(x,y,25),(x+30,y-12,32),(x+63,y,25)]:
        d.ellipse((cx-r*scale,cy-r*scale,cx+r*scale,cy+r*scale),fill=col,outline='#0B1F33',width=4)
    d.rounded_rectangle((x-25,y-4,x+88,y+27),14,fill=col)
    if face:
        d.ellipse((x+12,y-2,x+18,y+5),fill='#0B1F33'); d.ellipse((x+45,y-2,x+51,y+5),fill='#0B1F33')
        d.arc((x+24,y+8,x+40,y+18),0,180,fill='#0B1F33',width=3)

def card(d,x,y,w,h,title,value,sub,accent):
    d.rounded_rectangle((x,y,x+w,y+h),18,fill='#FFFFFF',outline='#D7E4ED',width=3)
    d.rounded_rectangle((x+10,y+10,x+22,y+h-10),6,fill=accent)
    d.text((x+34,y+18),title,font=fnt(19),fill='#0B1F33')
    d.text((x+34,y+48),value,font=fnt(28),fill='#0B1F33')
    d.text((x+34,y+86),sub,font=fnt(15,False),fill='#466276')

def render(snapshot_path: str, out: str):
    snap=json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    sc=build_script(snap)
    tmp=Path(tempfile.mkdtemp(prefix='previsaorj-'))
    wav=tmp/'voice.wav'
    # technical voice only; production workflow targets Kokoro.
    subprocess.run(['espeak','-v','pt-br','-s','155','-w',str(wav),sc['narration']],check=True)
    # extend/silence to stable duration, then encode frames directly
    video_noaudio=tmp/'video.mp4'
    cmd=['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
         '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(video_noaudio)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    locs=snap['forecast']['today']['locations']
    hot=max(locs,key=lambda z:z['max_c']); cool=min(locs,key=lambda z:z['max_c']); wet=max(locs,key=lambda z:z['rain_probability_pct'])
    total=int(DURATION*FPS)
    for i in range(total):
        t=i/FPS
        im=Image.new('RGB',(W,H),'#CFEFFF'); d=ImageDraw.Draw(im)
        # sky bands + skyline
        d.rectangle((0,0,W,320),fill='#66BFF2'); d.rectangle((0,320,W,H),fill='#EAF7FD')
        sunx=430+8*math.sin(t*.3); d.ellipse((sunx-38,70,sunx+38,146),fill='#FFD34E')
        draw_cloud(d,t,55,120,1.0,True); draw_cloud(d,t,290,190,.75,False)
        # skyline
        for x,bw,bh in [(0,65,150),(70,50,105),(126,78,180),(210,55,125),(272,90,165),(370,55,118),(430,75,155),(510,45,125)]:
            d.rectangle((x,320-bh,x+bw,320),fill='#7AA4BC')
        # header/watermark
        d.rounded_rectangle((22,22,235,68),16,fill='#0B1F33')
        d.text((38,34),'PREVISÃO RJ',font=fnt(22),fill='#FFFFFF')
        d.text((382,34),'@previsaorj',font=fnt(13),fill='#0B1F33')
        draw_bira(d,t)
        # content beats
        if t < 3.3:
            d.rounded_rectangle((36,365,504,535),24,fill='#0B1F33')
            centered(d,'HOJE VÃO EXISTIR',390,fnt(29),'#FFFFFF')
            centered(d,'DOIS RIOS',442,fnt(48),'#FFD34E')
            d.text((70,520),'temperatura + chance de chuva',font=fnt(17,False),fill='#466276')
        elif t < 8.2:
            d.text((245,372),'CONTRASTE DE HOJE',font=fnt(22),fill='#0B1F33')
            card(d,230,414,280,125,hot['name'],f"{hot['max_c']}°",'mais quente na amostra','#F59A4A')
            card(d,230,553,280,125,cool['name'],f"{cool['max_c']}°",'mais ameno na amostra','#58AEE8')
        elif t < 13.2:
            d.text((245,372),'CHUVA: ONDE OLHAR',font=fnt(22),fill='#0B1F33')
            d.rounded_rectangle((230,420,510,630),24,fill='#FFFFFF',outline='#D7E4ED',width=3)
            d.text((258,450),wet['name'],font=fnt(26),fill='#0B1F33')
            d.text((258,500),f"{wet['rain_probability_pct']}%",font=fnt(56),fill='#5E8DFF')
            d.text((258,575),'chance máxima na fixture técnica',font=fnt(15,False),fill='#466276')
            for k in range(4):
                xx=440+k*14; yy=535+(k%2)*8
                d.line((xx,yy,xx-5,yy+18),fill='#5E8DFF',width=4)
        else:
            d.rounded_rectangle((225,400,512,670),24,fill='#0B1F33')
            centered(d,'ANTES DE SAIR',432,fnt(28),'#FFFFFF',250)
            centered(d,'confira a atualização',490,fnt(23),'#FFD34E',250)
            centered(d,'do seu bairro',534,fnt(23),'#FFD34E',250)
            centered(d,'O tempo do Rio para decidir seu dia.',610,fnt(16,False),'#FFFFFF',245)
        # safe-area footer marker
        footer = "PILOTO TÉCNICO · dados de fixture" if str(snap.get("source","")).startswith("fixture") else "@previsaorj · atualização automática"
        d.text((260,900),footer,font=fnt(12,False),fill='#68869A')
        proc.stdin.write(im.tobytes())
    proc.stdin.close(); rc=proc.wait()
    if rc: raise RuntimeError('ffmpeg frame encode falhou')
    outp=Path(out); outp.parent.mkdir(parents=True,exist_ok=True)
    # mux, pad audio with silence, scale 2x to exact 1080x1920
    subprocess.run(['ffmpeg','-y','-i',str(video_noaudio),'-i',str(wav),'-filter_complex',
                    f"[0:v]scale=1080:1920[v];[1:a]apad=pad_dur={DURATION}[a]",
                    '-map','[v]','-map','[a]','-t',str(DURATION),'-c:v','libx264','-preset','medium','-crf','19',
                    '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(outp)],check=True,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    from src.previsao_rj.publish.caption import build_caption
    cap=build_caption(snap)
    (outp.parent/'LEGENDA_TESTE_01.txt').write_text(cap,encoding='utf-8')
    (outp.parent/'roteiro_teste_01.json').write_text(json.dumps(sc,ensure_ascii=False,indent=2),encoding='utf-8')
    print(outp)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--fixture',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); render(a.fixture,a.out)
if __name__=='__main__': main()

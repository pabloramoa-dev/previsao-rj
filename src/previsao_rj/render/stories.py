"""Stories vetoriais 1080×1920: Manrope, Meteocons e resvg, sem rede no render."""
import argparse
import base64
from datetime import datetime
from html import escape
import json
import math
from pathlib import Path
import resvg_py
from PIL import ImageFont

ASSETS = Path(__file__).with_name('story_assets')


def num(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def fmt(value,suffix=''):
    return (f'{value:g}'.replace('.',',')+suffix) if num(value) else '—'


def weather(code):
    if code==0:return 'clear-day','Céu aberto'
    if code in (1,2):return 'partly-cloudy-day','Sol entre nuvens'
    if code==3:return 'overcast','Céu nublado'
    if code in (45,48):return 'fog','Nevoeiro'
    if code in (51,53,55,56,57):return 'drizzle','Possibilidade de garoa'
    if code in (61,63,65,66,67,80,81,82):return 'rain','Previsão de chuva'
    if code in (71,73,75,77,85,86):return 'snow','Precipitação invernal'
    if code in (95,96,99):return 'thunderstorms-rain','Previsão de tempestade'
    return 'not-available','Condição indisponível'


def text(x,y,value,size=32,fill='#ECF4F7',weight=400,anchor='start',spacing=0):
    return f'<text x="{x}" y="{y}" font-family="Manrope" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}">{escape(str(value))}</text>'


def fitted(value,max_width,size=90):
    font=ASSETS/'Manrope-Bold.ttf'
    while size>30 and ImageFont.truetype(str(font),size).getlength(value)>max_width:size-=2
    return size


def icon(name,x,y,size):
    data=base64.b64encode((ASSETS/(name+'.svg')).read_bytes()).decode()
    return f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>'


def rect(x,y,w,h,fill,rx=26,stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'


def hourly_sample(loc,generated,day):
    rows=[]
    for row in loc.get('hourly',[]):
        try:stamp=datetime.fromisoformat(row['time'])
        except (KeyError,TypeError,ValueError):continue
        if stamp.tzinfo is None or stamp.date().isoformat()!=day or stamp<generated:continue
        if stamp.hour%3==0:rows.append(row)
    return rows[:4]


def svg_card(snapshot,loc,preview=False):
    day=snapshot['forecast']['today']['date'];generated=datetime.fromisoformat(snapshot['generated_at'])
    date=datetime.fromisoformat(day)
    weekdays=['SEG','TER','QUA','QUI','SEX','SÁB','DOM']
    mint='#84E9D0';muted='#A3BAC8'
    symbol,condition=weather(loc.get('weather_code'))
    municipality=loc.get('municipality','').replace('_',' ').title().replace('De ','de ')
    label='ESTUDO VISUAL' if preview else 'PREVISÃO DO DIA'
    parts=['''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><defs>
    <linearGradient id="bg" x2="0.85" y2="1"><stop stop-color="#07192D"/><stop offset=".6" stop-color="#12374A"/><stop offset="1" stop-color="#092737"/></linearGradient>
    <radialGradient id="glow"><stop stop-color="#347681" stop-opacity=".45"/><stop offset="1" stop-color="#347681" stop-opacity="0"/></radialGradient>
    <linearGradient id="panel" x2="1" y2="1"><stop stop-color="#234A5F" stop-opacity=".8"/><stop offset="1" stop-color="#17364A" stop-opacity=".75"/></linearGradient>
    </defs><rect width="1080" height="1920" fill="url(#bg)"/><ellipse cx="850" cy="570" rx="590" ry="670" fill="url(#glow)"/>
    <g stroke="#76C1C3" stroke-opacity=".07" fill="none" stroke-width="2">''']
    for i in range(8):parts.append(f'<path d="M {650+i*38} -30 C {390+i*38} 280,{1230+i*38} 370,{650+i*38} 890"/>')
    parts+=['</g>',rect(72,179,48,48,mint,14),text(96,212,'RJ',22,'#082537',800,'middle'),text(138,212,'PREVISÃO RJ',30,weight=800,spacing=1),text(1008,212,label,19,mint,700,'end',2)]
    parts +=[rect(72,273,235,48,'#244859',24),text(189,306,f"{weekdays[date.weekday()]}  •  {date:%d.%m}",22,'#D5E8EB',600,'middle')]
    name=loc['name']
    parts +=[text(72,420,name,fitted(name,936),weight=800),text(76,471,('Baixada Fluminense' if loc.get('municipality') in {'duque_de_caxias','nova_iguacu'} else municipality or 'Rio metropolitano'),29,muted)]
    parts +=[text(76,555,'MÁXIMA PREVISTA',22,mint,700,spacing=3),text(66,747,fmt(loc.get('max_c'),'°'),210,weight=800),text(80,810,'Mínima '+fmt(loc.get('min_c'),'°'),36,'#C8DEE5',600),icon(symbol,562,482,420),text(774,851,condition,24,'#D0E1E5',600,'middle')]
    cards=[('raindrop','CHUVA NO DIA',fmt(loc.get('rain_probability_pct'),'%'),'probabilidade'),('wind','RAJADAS',fmt(loc.get('wind_gust_max_kmh')),'km/h'),('uv-index','ÍNDICE UV',fmt(loc.get('uv_index_max')),'máximo previsto')]
    for i,(im,title,value,unit) in enumerate(cards):
        x=72+i*320
        parts +=[rect(x,914,296,224,'url(#panel)',28,'#426071'),icon(im,x+18,932,66),text(x+28,1039,title,18,muted,700,spacing=1),text(x+28,1105,value,54,weight=800),text(x+266,1104,unit,15,muted,400,'end') if unit=='km/h' else text(x+28,1130,unit,16,muted)]
    parts +=[text(76,1210,'AO LONGO DO DIA',23,mint,700,spacing=2),text(1005,1210,'temperatura / chance de chuva',18,muted,400,'end')]
    rows=hourly_sample(loc,generated,day)
    for i in range(4):
        x=72+i*240
        parts +=[rect(x,1242,216,202,'#102F43',22)]
        if i<len(rows):
            row=rows[i];hour=datetime.fromisoformat(row['time']).strftime('%Hh')
            p=row.get('precipitation_probability');temp=row.get('temperature_2m')
            parts +=[text(x+108,1286,hour,24,muted,600,'middle'),text(x+108,1344,fmt(temp,'°'),42,weight=700,anchor='middle'),text(x+108,1400,fmt(p,'%'),23,'#90DAD9',600,'middle')]
            if num(p):parts +=[rect(x+36,1415,144,5,'#294B60',2),rect(x+36,1415,144*max(0,min(100,p))/100,5,mint,2)]
        else:parts +=[text(x+108,1326,'—',38,muted,anchor='middle'),text(x+108,1375,'sem horário',18,muted,anchor='middle')]
    parts +=[text(76,1500,'Probabilidade não significa chuva o dia inteiro.',25,'#AFC7D1'),'<path d="M72 1560 H1008" stroke="#426071"/>',text(74,1620,'O tempo muda. Vá informado.',35,weight=700),text(76,1680,'@previsaorj',25,mint,700),text(1008,1680,f'Coleta {generated:%d/%m • %H:%M}',21,muted,400,'end')]
    if preview:parts +=[text(540,1775,'PRÉVIA DE DESIGN • DADOS DA COLETA INDICADA',18,muted,anchor='middle',spacing=1)]
    parts +=['</svg>']
    return ''.join(parts)


def generate(snapshot,destination,reference=None,*,preview=False):
    from ..normalizers.snapshot import is_stale
    if not preview and is_stale(snapshot,reference=reference):raise ValueError('Snapshot vencido')
    out=Path(destination);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for loc in snapshot['forecast']['today']['locations']:
        markup=svg_card(snapshot,loc,preview)
        png=resvg_py.svg_to_bytes(svg_string=markup,font_files=[str(ASSETS/'Manrope-Regular.ttf'),str(ASSETS/'Manrope-Bold.ttf')],skip_system_fonts=True)
        path=out/(loc['id']+'.png');path.write_bytes(png);results.append(str(path))
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('snapshot');p.add_argument('out');p.add_argument('--preview',action='store_true',help='Prévia marcada, permite coleta histórica; não publica')
    args=p.parse_args();print('\n'.join(generate(json.loads(Path(args.snapshot).read_text()),args.out,preview=args.preview)))

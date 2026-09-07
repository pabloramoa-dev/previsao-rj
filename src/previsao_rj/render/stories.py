"""Cards por local em 1080x1920, somente geração de arquivos."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from ..normalizers.snapshot import is_stale


def generate(snapshot, destination, reference=None):
    if is_stale(snapshot, reference=reference): raise ValueError('Snapshot vencido')
    out=Path(destination);out.mkdir(parents=True,exist_ok=True)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    def font(size): return ImageFont.truetype(font_path,size)
    results=[]
    for loc in snapshot['forecast']['today']['locations']:
        img=Image.new('RGB',(1080,1920),'#122E43');d=ImageDraw.Draw(img)
        d.rounded_rectangle((64,270,1016,1590),radius=48,fill='#F3F6EF')
        d.text((80,170),'PREVISÃO RJ',font=font(44),fill='#FFD166')
        name=loc['name'];size=66
        while d.textbbox((0,0),name,font=font(size))[2]>840: size-=2
        d.text((112,345),name,font=font(size),fill='#122E43')
        d.text((112,445),snapshot['forecast']['today'].get('date','HOJE'),font=font(35),fill='#007F87')
        def val(key,unit): return f'{loc[key]}{unit}' if loc.get(key) is not None else 'Indisponível'
        for y,label,value in [(605,'MÍNIMA / MÁXIMA',val('min_c','°')+' / '+val('max_c','°')),
                              (870,'PROBABILIDADE DE CHUVA',val('rain_probability_pct','%')),
                              (1135,'RAJADAS PREVISTAS',val('wind_gust_max_kmh',' km/h'))]:
            d.text((112,y),label,font=font(30),fill='#007F87')
            size=72
            while d.textbbox((0,0),value,font=font(size))[2]>840:size-=2
            d.text((112,y+60),value,font=font(size),fill='#122E43')
        d.text((112,1450),'Chuva pode ocorrer em intervalos.',font=font(32),fill='#122E43')
        d.text((80,1670),'Atualizado: '+snapshot['generated_at'],font=font(25),fill='white')
        d.text((80,1730),'Confira a previsão antes de sair.',font=font(34),fill='white')
        path=out/(loc['id']+'.png');img.save(path);results.append(str(path))
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('snapshot');p.add_argument('out');args=p.parse_args()
    print('\n'.join(generate(json.loads(Path(args.snapshot).read_text()),args.out)))

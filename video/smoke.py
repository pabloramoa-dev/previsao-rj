"""Render three real compositions and verify audio/duration without publishing."""
from pathlib import Path
import json
import math
import struct
import subprocess
from video.compositor import apply, run

out = Path('output/hyperframes-validation')
out.mkdir(parents=True, exist_ok=True)
source = out/'base.mp4'
run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
     'testsrc2=size=1080x1920:rate=30','-f','lavfi','-i',
     'sine=frequency=440:sample_rate=48000','-t','2',
     '-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac',source])

def samples(path):
    data = subprocess.check_output(['ffmpeg','-v','error','-i',str(path),
        '-vn','-f','f32le','-ar','48000','-ac','1','-'])
    return struct.unpack('<'+'f'*(len(data)//4), data)

original = samples(source)
for style in ('guru','rj'):
    final = out/(style+'.mp4')
    apply(source, final, cuts=[.7, 1.4], style=style)
    info = json.loads(final.with_suffix('.render.json').read_text())
    assert info['motor']=='hyperframes'
    result = samples(final)
    n = min(len(original),len(result),90000)
    a,b=original[2000:n],result[2000:n]
    correlation=sum(x*y for x,y in zip(a,b))/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    assert correlation > .98, ('Audio changed',style,correlation)
    print(style, 'audio correlation:',round(correlation,5))
    run(['ffmpeg','-y','-v','error','-ss','0.8','-i',final,'-frames:v','1',out/(style+'.png')])

# Native Rio bulletin: same news visual language as the approved reference.
from video.boletim import render
beats = [
    {'tipo':'nenhum','fala':'Veja como fica o tempo no Rio hoje.','legenda':'Veja o tempo no Rio'},
    {'tipo':'gancho','fala':'Maxima prevista de vinte e oito graus.','legenda':'28 graus previstos'}]
segments=[{'ini':0.,'fim':.9},{'ini':1.,'fim':2.}]
final=out/'rj-boletim.mp4'
import shutil
shutil.copy2(source, final)
render(final,beats,segments,character='bira',date='01/10',hour='06:00',root=Path.cwd())
run(['ffmpeg','-y','-v','error','-ss','0.8','-i',final,'-frames:v','1',out/'rj-boletim.png'])

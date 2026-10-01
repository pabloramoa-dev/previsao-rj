"""Previsão RJ: the approved Sulflu news language, with the Rio cast/data.

The original scene supplies Bira/Bia, lip sync, scenery and data panels.
HyperFrames supplies the news HUD, ticker, captions, cuts and sound design.
"""
import html
import json
import math
from pathlib import Path
import re
import shutil

from .compositor import apply, run


def escape(text):
    return html.escape(str(text), quote=True)


def compose(work, duration, width, height, cuts, style, *, beats, segments, character, date, hour):
    if (width, height) != (1080, 1920):
        raise ValueError('Boletim RJ requires 1080x1920')
    if len(beats) != len(segments):
        raise ValueError('Beats/segments mismatch')
    names = {'bira': 'BIRA DO TEMPO', 'bia': 'BIA DA ORLA', 'maria': 'DONA MARIA', 'ranzinza': 'SEU RANZINZA'}
    captions, animations = [], []
    for i, (beat, seg) in enumerate(zip(beats, segments)):
        if beat['tipo'] in ('gancho', 'cta', 'resumo', 'fecho'):
            continue  # Full original data panel / CTA takes priority.
        start, end = float(seg['ini']), float(seg['fim'])
        if not (0 <= start < end <= duration + .05):
            raise ValueError('Caption outside narration')
        words = beat.get('legenda', beat['fala']).split()
        pages = [words[k:k+4] for k in range(0, len(words), 4)]
        for k, page in enumerate(pages):
            a = start + (end-start)*k/len(pages)
            length = (end-start)/len(pages)
            spans=[]
            for j, word in enumerate(page):
                ident=f'w{i}_{k}_{j}'
                spans.append(f'<span id="{ident}">{escape(word)}</span>')
                t=a+length*j/len(page)
                animations.append(f'tl.set("#{ident}",{{backgroundColor:"#d63a2f",scale:1.06}},{t});')
            captions.append(f'<div id="caption{i}_{k}" class="clip caption" data-start="{a}" data-duration="{length}" data-track-index="4">{" ".join(spans)}</div>')
    for k,t in enumerate(cuts):
        effect = k % 3
        if effect == 0:
            for j,(x,skew) in enumerate([(-14,2),(18,-2),(-8,1),(0,0)]):
                animations.append(f'tl.set("#base",{{x:{x},skewX:{skew}}},{t+j/30});')
            animations.append(f'tl.fromTo("#glitch",{{opacity:.18}},{{opacity:0,duration:.18,immediateRender:false}},{t});')
        elif effect == 1:
            animations.append(f'tl.fromTo("#base",{{x:24,filter:"blur(8px)"}},{{x:0,filter:"blur(0px)",duration:.22,immediateRender:false,ease:"power3.out"}},{t});')
        else:
            animations.append(f'tl.fromTo("#flash",{{opacity:.25}},{{opacity:0,duration:.22,immediateRender:false}},{t});')
    animations += [
        'tl.fromTo("#hud",{y:-130},{y:0,duration:.35,ease:"back.out(1.5)"},0);',
        f'tl.to("#dot",{{opacity:.3,duration:.45,repeat:{max(0,math.ceil(duration/.45)-1)},yoyo:true,ease:"steps(1)"}},0);',
        'tl.fromTo("#lower",{x:-100,opacity:0},{x:0,opacity:1,duration:.35,ease:"power3.out"},.5);',
        f'tl.to("#lower",{{opacity:0,duration:.25}},{min(4.,max(.9,duration-.4))});',
        f'tl.fromTo("#ticker-track",{{x:0}},{{x:-document.querySelector("#ticker-copy").offsetWidth,duration:{duration},ease:"none"}},0);',
        f'tl.fromTo("#progress",{{scaleX:0}},{{scaleX:1,duration:{duration},ease:"none"}},0);']
    for k in range(math.ceil(duration*8)):
        animations.append(f'tl.set("#grain",{{x:{k*37%12-6},y:{k*53%12-6}}},{k/8});')
    ticker_text=' · '.join(escape(b.get('legenda') or b['fala']) for b in beats if b['tipo'] not in ('cta','fecho'))
    page=f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face{{font-family:Local;src:url(assets/bold.ttf)}}
*{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#0b1624}}
#root{{position:relative;width:1080px;height:1920px;font-family:Local,sans-serif;color:white;overflow:hidden}}
#base{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}
#hud{{position:absolute;top:120px;left:36px;right:36px;display:flex;gap:12px;align-items:center;font-size:36px}}
.red{{background:#d63a2f;padding:8px 16px;border:4px solid #1c1c1e;border-radius:10px}}
#dot{{display:inline-block;width:14px;height:14px;margin-right:10px;background:white;border-radius:50%}}
.brand{{flex:1;background:#13243a;padding:10px 16px;border:4px solid #1c1c1e;border-radius:10px}}
.clock{{background:#ffd34e;color:#1c1c1e;padding:10px 14px;border:4px solid #1c1c1e;border-radius:10px}}
#lower{{position:absolute;left:80px;top:1330px;background:white;color:#1c1c1e;padding:14px 22px;font-size:42px;box-shadow:9px 9px 0 #d63a2f}}
#lower small{{display:block;font-size:24px;color:#8b2420;margin-top:5px}}
.caption{{position:absolute;top:1510px;left:65px;width:950px;min-height:105px;display:flex;justify-content:center;align-content:center;flex-wrap:wrap;gap:8px 10px;font-size:48px;line-height:1.2;text-align:center}}
.caption span{{background:rgba(11,22,36,.94);padding:6px 12px;border-radius:12px;max-width:950px;overflow-wrap:anywhere;text-shadow:0 3px #1c1c1e}}
#ticker{{position:absolute;left:0;right:0;top:1690px;height:66px;display:flex;background:white;color:#1c1c1e;border-block:4px solid #1c1c1e}}
#ticker b{{background:#d63a2f;color:white;font-size:32px;padding:10px 22px;flex-shrink:0}}
#ticker-window{{position:relative;flex:1;overflow:hidden}}
#ticker-track{{position:absolute;display:flex;white-space:nowrap;font-size:34px;line-height:57px}}
.ticker-copy{{padding-right:60px}}
#grain{{position:absolute;inset:-12px;opacity:.045;background:repeating-radial-gradient(circle at 17% 32%,white 0 1px,transparent 1px 3px);pointer-events:none}}
#vignette{{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 45%,transparent 68%,rgba(0,0,0,.18));pointer-events:none}}
#glitch{{position:absolute;inset:0;opacity:0;background:repeating-linear-gradient(0deg,#d63a2f 0 12px,transparent 12px 100px);mix-blend-mode:screen}}
#flash{{position:absolute;inset:0;background:white;opacity:0}}
#progress{{position:absolute;left:70px;bottom:125px;width:940px;height:6px;background:#ffd34e;transform-origin:left}}
</style></head><body><div id="root" data-composition-id="rj-boletim" data-width="1080" data-height="1920" data-duration="{duration}" data-fps="30">
<video id="base" class="clip" src="assets/base.mp4" data-start="0" data-duration="{duration}" data-track-index="0" muted playsinline></video>
<div id="grain"></div><div id="vignette"></div><div id="glitch"></div><div id="flash"></div>
<header id="hud"><div class="red"><i id="dot"></i>PREVISÃO</div><div class="brand">PREVISÃO RJ · {escape(date)}</div><div class="clock">{escape(hour)}</div></header>
<div id="lower">{names[character]}<small>TEMPO NO RIO DE JANEIRO</small></div>
{''.join(captions)}
<div id="ticker"><b>RIO</b><div id="ticker-window"><div id="ticker-track"><span class="ticker-copy" id="ticker-copy">{ticker_text}</span><span class="ticker-copy">{ticker_text}</span></div></div></div><div id="progress"></div>
<audio id="audio" src="assets/mix.wav" data-start="0" data-duration="{duration}" data-track-index="8"></audio>
<script src="assets/gsap.min.js"></script><script>const tl=gsap.timeline({{paused:true}});{''.join(animations)}window.__timelines={{'rj-boletim':tl}};</script>
</div></body></html>'''
    work=Path(work)
    (work/'assets').mkdir(parents=True,exist_ok=True)
    shutil.copy2('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',work/'assets/bold.ttf')
    (work/'index.html').write_text(page,encoding='utf-8')
    return page


def mix(audio, duration, cuts):
    import numpy as np
    import soundfile as sf
    sr=48000
    bed=np.zeros(math.ceil(duration*sr))
    rng=np.random.default_rng(6)
    for t0 in np.arange(0,duration,60/110):
        a=int(t0*sr);n=min(len(bed)-a,int(.2*sr));t=np.arange(n)/sr
        bed[a:a+n]+=.008*np.sin(2*np.pi*65*t)*np.exp(-t*24)
    for t0 in cuts:
        a=int(t0*sr);n=min(len(bed)-a,int(.25*sr));t=np.arange(n)/sr
        bed[a:a+n]+=.012*rng.normal(size=n)*np.sin(np.pi*t/.25)**2
    if len(bed)>sr//4:bed[-sr//4:]*=np.linspace(1,0,sr//4)
    sf.write(audio.with_name('bed.wav'),bed,sr)
    final=audio.with_name('mix-master.wav')
    run(['ffmpeg','-y','-v','error','-i',audio,'-i',audio.with_name('bed.wav'),
         '-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=disabled:latency=1[a]',
         '-map','[a]','-ar',sr,final])
    final.replace(audio)


def render(source, beats, segments, *, character, date, hour, root):
    def page(work, duration, width, height, cuts, style):
        return compose(work,duration,width,height,cuts,style,beats=beats,
                       segments=segments,character=character,date=date,hour=hour)
    return apply(source,root=root,cuts=[s['ini'] for s in segments[1:]],
                 style='rj',compose=page,mix=mix)

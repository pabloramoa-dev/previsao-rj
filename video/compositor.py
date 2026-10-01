"""HyperFrames finishing layer over the original character/card render.

Original art, captions, narration and music remain in the source layer.
No fallback: a missing compositor or failed render stops delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

VERSION = '0.8.96'
PALETTES = {'guru': ('#17102c', '#eac671'),
            'rj': ('#102c43', '#69ddd0'),
            'vr': ('#15283f', '#ffc65c')}


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format',
        '-of', 'json', str(path)]))


def timeline(duration, cuts):
    duration = float(duration)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid duration')
    values = sorted(set(float(t) for t in cuts))
    if any(not math.isfinite(t) or t < 0 or t >= duration for t in values):
        raise ValueError('Cut outside source timeline')
    return duration, [t for t in values if t > 0]


def composition(work, duration, width, height, cuts=(), style='guru'):
    duration, cuts = timeline(duration, cuts)
    background, accent = PALETTES[style]
    # Side particles never cross the original labels, map or faces.
    dots, animations = [], []
    for i in range(14):
        x = width * (.014 if i % 2 else .986)
        y = height * (.1 + (i % 7) * .115)
        size = width * (.003 + (i % 3) * .001)
        dots.append(f'<i id="p{i}" class="particle" style="left:{x}px;top:{y}px;width:{size}px;height:{size}px"></i>')
        animations.append(f'tl.to("#p{i}",{{y:-{height*.02},opacity:.18,duration:{2+i%3},repeat:-1,yoyo:true,ease:"sine.inOut"}},0);')
    for t in cuts:
        animations.append(f'tl.fromTo("#edge",{{opacity:.85}},{{opacity:.08,duration:.45,immediateRender:false}},{t});')
    # Gentle movement zooms OUT and returns: no source content is cropped.
    # Meteorological cards remain fixed so every number stays readable.
    if style == 'guru':
        animations.append('tl.to("#base",{scale:.992,duration:4,repeat:-1,yoyo:true,ease:"sine.inOut"},0);')
    animations.append(f'tl.fromTo("#progress",{{scaleX:0}},{{scaleX:1,duration:{duration},ease:"none"}},0);')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:{background}}}
#root{{position:relative;width:{width}px;height:{height}px;overflow:hidden}}
#base{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;transform-origin:center}}
#edge{{position:absolute;inset:0;border:3px solid {accent};box-shadow:inset 0 0 20px {accent};opacity:.08;pointer-events:none}}
.particle{{position:absolute;border-radius:50%;background:{accent};opacity:.45;pointer-events:none}}
#progress{{position:absolute;left:7%;bottom:5.5%;width:86%;height:5px;border-radius:3px;background:{accent};transform-origin:left}}
</style></head><body><div id="root" data-composition-id="pipeline-hf" data-width="{width}" data-height="{height}" data-duration="{duration}" data-fps="30">
<video id="base" class="clip" src="assets/base.mp4" data-start="0" data-duration="{duration}" data-track-index="0" muted playsinline></video>
{''.join(dots)}<div id="edge"></div><div id="progress"></div>
<audio id="audio" src="assets/mix.wav" data-start="0" data-duration="{duration}" data-track-index="1"></audio>
<script src="assets/gsap.min.js"></script><script>const tl=gsap.timeline({{paused:true}});{''.join(animations)}window.__timelines={{'pipeline-hf':tl}};</script>
</div></body></html>'''
    Path(work).mkdir(parents=True, exist_ok=True)
    (Path(work) / 'index.html').write_text(page, encoding='utf-8')
    return page


def validate(path, duration, width, height):
    info = probe(path)
    videos = [s for s in info['streams'] if s['codec_type'] == 'video']
    audios = [s for s in info['streams'] if s['codec_type'] == 'audio']
    if len(videos) != 1 or not audios:
        raise ValueError('Missing video/audio stream')
    v = videos[0]
    if (v['width'], v['height'], v['codec_name'], v['avg_frame_rate']) != (width, height, 'h264', '30/1'):
        raise ValueError('Invalid resolution, codec or frame rate')
    if abs(float(info['format']['duration']) - duration) > .15:
        raise ValueError('Duration changed during composition')
    if audios[0]['codec_name'] != 'aac':
        raise ValueError('Invalid audio codec')
    run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-'])
    return info


def apply(source, destination=None, *, root=None, cuts=(), style='guru', compose=None, mix=None):
    source = Path(source).resolve()
    destination = Path(destination or source).resolve()
    root = Path(root or Path(__file__).resolve().parents[1])
    video = root / 'video'
    cli = video / 'node_modules/hyperframes/bin/hyperframes.mjs'
    if not cli.is_file():
        raise FileNotFoundError('HyperFrames missing: npm ci --prefix video and hyperframes browser ensure')
    info = probe(source)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    width, height = int(v['width']), int(v['height'])
    duration, cuts = timeline(float(v.get('duration') or info['format']['duration']), cuts)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    work = destination.parent / ('.hyperframes_' + destination.stem)
    assets = work / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    run(['ffmpeg', '-y', '-v', 'error', '-i', source, '-map', '0:v:0',
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-r', '30',
         '-g', '30', '-keyint_min', '30', '-sc_threshold', '0',
         '-pix_fmt', 'yuv420p', '-an', assets / 'base.mp4'])
    if any(s['codec_type'] == 'audio' for s in info['streams']):
        run(['ffmpeg', '-y', '-v', 'error', '-i', source, '-vn', '-af',
             f'apad,atrim=duration={duration}', '-ar', '48000', '-ac', '2', assets / 'mix.wav'])
    else:
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
             'anullsrc=r=48000:cl=stereo', '-t', duration, assets / 'mix.wav'])
    shutil.copy2(video / 'node_modules/gsap/dist/gsap.min.js', assets / 'gsap.min.js')
    (compose or composition)(work, duration, width, height, cuts, style)
    if mix:
        mix(assets / 'mix.wav', duration, cuts)
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1', DO_NOT_TRACK='1',
               HYPERFRAMES_FFMPEG_PATH=shutil.which('ffmpeg') or 'ffmpeg',
               HYPERFRAMES_FFPROBE_PATH=shutil.which('ffprobe') or 'ffprobe')
    run(['node', cli, 'lint', work], env=env)
    temporary = destination.with_name(destination.stem + '.rendering.mp4')
    run(['node', cli, 'render', work, '--output', temporary, '--workers',
         os.environ.get('HYPERFRAMES_WORKERS', '2'), '--no-browser-gpu'], env=env)
    validate(temporary, duration, width, height)
    temporary.replace(destination)
    destination.with_suffix('.render.json').write_text(json.dumps({
        'motor': 'hyperframes', 'version': VERSION, 'style': style,
        'duration': duration, 'resolution': [width, height], 'fps': 30,
        'source_sha256': source_hash, 'cuts': cuts,
        'original_audio': True, 'original_captions': True}, indent=2) + '\n')
    shutil.rmtree(work)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output')
    parser.add_argument('--style', choices=PALETTES, default='guru')
    args = parser.parse_args()
    apply(args.source, args.output, style=args.style)

# -*- coding: utf-8 -*-
"""
gerar_hf.py — o Reel do @previsaorj feito INTEIRO com HyperFrames (HTML -> vídeo).

Estúdio completo, no mesmo molde do motor aprovado em 30/09/2026: o Manim sai
da produção diária e a imagem inteira passa a ser HTML + GSAP renderizado pelo
HyperFrames. Continua IGUAL ao que já estava aprovado no RJ:

  - roteiro e pauta  -> src/previsao_rj/editorial (prepare + corte de duração)
  - voz              -> Kokoro local (Bira = pm_alex 1.04 · Bia = pf_dora 1.02)
  - lip sync         -> energia do áudio (render/characters/amplitude.py)
  - cinco previsões  -> Niterói, Centro do Rio, Zona Sul, Baixada, Campo Grande
  - QA, preview 720p, miniatura e manifesto no mesmo lugar de antes

Muda a camada visual (hyperframes/compor.py): Bira/Bia redesenhados em SVG
animado, telão com a paisagem do Rio pelo tempo do dia, número com count-up e
headline-slam, quadro split-flap das cinco regiões, alerta com carimbo,
transições glitch / whip-pan / flash, HUD de telejornal, ticker, lower third,
legenda karaokê, card "Seguir" (sub-composição) e trilha + whooshes sintetizados.

Reversão sem editar código: PREVISAO_RJ_MOTOR=manim usa o pipeline antigo.

Uso (mesmos argumentos do pipeline Manim):
    python hyperframes/gerar_hf.py --demo --personagem bira --out output/REEL.mp4
    python hyperframes/gerar_hf.py --snapshot output/snapshot.json \
        --personagem bia --format amanha_no_rio --out output/REEL.mp4
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))

from src.previsao_rj.render.characters.amplitude import gerar_cues  # noqa: E402
from src.previsao_rj.render.characters.pipeline import PRESETS  # noqa: E402

PACKAGE = 'src.previsao_rj.render.characters'
VERSAO_HF = '0.8.96'
CAUDA = 0.9          # respiro depois do fecho, para o card "Seguir" terminar
TRANS_DUR = 0.45
BUILD = AQUI / 'build'
AUDIO = AQUI / 'assets' / 'audio'
CLI = RAIZ / 'video' / 'node_modules' / 'hyperframes' / 'bin' / 'hyperframes.mjs'
FILTRO_VOZ = 'highpass=f=80,acompressor=threshold=-18dB:ratio=2:attack=8:release=180,volume=1.1'
DEMO_SNAPSHOT = RAIZ / 'tests' / 'fixtures' / 'snapshot_rj.json'

MESES = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
         'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
DIAS = ['SEGUNDA', 'TERÇA', 'QUARTA', 'QUINTA', 'SEXTA', 'SÁBADO', 'DOMINGO']


def run(cmd, **kw):
    subprocess.run([str(x) for x in cmd], check=True, **kw)


# ---------------------------------------------------------------- áudio ---
def ler_wav(caminho):
    with wave.open(str(caminho), 'rb') as w:
        n, sr, ch, larg = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
        x = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[larg]).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x / (32768.0 if larg == 2 else 2147483648.0), sr


def gravar_wav(caminho, x, sr, estereo=False):
    x = np.clip(x, -1, 1)
    if estereo and x.ndim == 1:
        x = np.stack([x, x], axis=1)
    pcm = (x * 32767).astype(np.int16)
    with wave.open(str(caminho), 'wb') as w:
        w.setnchannels(2 if pcm.ndim == 2 else 1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def tempos_das_palavras(texto, ini, fim):
    """Distribui as palavras da batida no tempo real da fala. Peso = sílabas
    aproximadas (vogais) + pausa na pontuação, que o Kokoro respeita."""
    palavras = texto.split()
    pesos = []
    for p in palavras:
        v = len(re.findall(r'[aeiouáéíóúâêôãõà0-9]', p.lower())) or 1
        pausa = 1.6 if p[-1] in '.!?' else (0.9 if p[-1] in ',:;' else 0.0)
        pesos.append((v, pausa))
    total = sum(v + pa for v, pa in pesos) or 1
    t, out = ini, []
    for p, (v, pa) in zip(palavras, pesos):
        d_fala = (fim - ini) * v / total
        out.append({'w': p, 's': round(t, 3), 'e': round(t + d_fala, 3)})
        t += d_fala + (fim - ini) * pa / total
    return out


def trilha(dur, cortes, sr):
    """Cama de telejornal sintetizada (sem licença de terceiros): pulso grave em
    110 BPM, acorde suspenso, chimbal depois do gancho e um 'ding' de abertura.
    Whooshes de ruído filtrado nos cortes de cena."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    beat = 60 / 110
    x = np.zeros(n, dtype=np.float32)
    for k in range(int(dur / beat) + 1):
        a = int(k * beat * sr)
        m = min(n - a, int(0.25 * sr))
        if m <= 0:
            continue
        tt = np.arange(m) / sr
        f = 55 + 60 * np.exp(-tt * 30)
        x[a:a + m] += 0.55 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 14)
    for fr in (146.83, 220.0, 329.63):      # Dsus2 baixinho, com trêmulo lento
        x += 0.05 * np.sin(2 * np.pi * fr * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t))
    rng = np.random.default_rng(6)
    for k in range(int(dur / (beat / 2)) + 1):
        a = int(k * beat / 2 * sr)
        if a / sr < 1.8:
            continue
        m = min(n - a, int(0.04 * sr))
        if m <= 0:
            continue
        ruido = np.diff(rng.standard_normal(m).astype(np.float32), prepend=0)
        x[a:a + m] += 0.05 * ruido * np.exp(-np.arange(m) / sr * 90)
    for ini, fr in ((0.0, 987.77), (0.16, 1318.5)):
        a = int(ini * sr)
        m = min(n - a, int(0.9 * sr))
        tt = np.arange(m) / sr
        x[a:a + m] += 0.28 * np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 5)
    fade = int(0.4 * sr)
    x[-fade:] *= np.linspace(1, 0, fade)
    trilha_x = x / (np.abs(x).max() or 1) * 0.9

    sfx = np.zeros(n, dtype=np.float32)
    for c in cortes:
        a = int(max(0, c - 0.18) * sr)
        m = min(n - a, int(0.55 * sr))
        if m <= 0:
            continue
        tt = np.arange(m) / sr
        ruido = rng.standard_normal(m).astype(np.float32)
        y = np.zeros(m, dtype=np.float32)
        alpha = np.linspace(0.02, 0.5, m)
        acc = 0.0
        for j in range(m):
            acc += alpha[j] * (ruido[j] - acc)
            y[j] = acc
        sfx[a:a + m] += y * np.sin(np.pi * np.clip(tt / 0.55, 0, 1)) ** 2
    sfx = sfx / (np.abs(sfx).max() or 1) * 0.8
    return trilha_x, sfx


# ---------------------------------------------------------------- dados ---
def bloco_do_formato(snapshot, formato):
    if formato == 'amanha_no_rio':
        return snapshot['forecast'].get('tomorrow') or snapshot['forecast']['today']
    return snapshot['forecast']['today']


def ceu_do_dia(locs):
    """Céu do telão pelo tempo previsto (mesma ideia do cenário pelo tempo)."""
    def num(v):
        return isinstance(v, (int, float)) and v == v
    chuva = max([l['rain_probability_pct'] for l in locs if num(l.get('rain_probability_pct'))] or [0])
    mm = max([l['rain_mm'] for l in locs if num(l.get('rain_mm'))] or [0])
    maxima = max([l['max_c'] for l in locs if num(l.get('max_c'))] or [28])
    if chuva >= 70 and mm >= 15:
        return 'tempestade'
    if chuva >= 60:
        return 'chuva'
    if chuva >= 40:
        return 'nublado'
    if maxima >= 34:
        return 'calor'
    if maxima <= 20:
        return 'frio'
    return 'sol'


def demo_batidas(personagem):
    """Demonstração realista: roteiro de produção sobre a fixture técnica,
    sem a trava de frescor (nunca publica)."""
    from src.previsao_rj.editorial.formats import amanha_no_rio, rio_antes_de_sair
    # A coleta real mais recente guardada no repositório mostra as cinco
    # regiões; a fixture técnica fica de reserva.
    guardados = sorted((RAIZ / 'data' / 'snapshots').glob('20*.json'))
    fonte = guardados[-1] if guardados else DEMO_SNAPSHOT
    snap = json.loads(fonte.read_text(encoding='utf-8'))
    print(f'[demo] dados de {fonte.name} (sem publicação)')
    formato = 'amanha_no_rio' if personagem == 'bia' else 'rio_antes_de_sair'
    fn = amanha_no_rio if formato == 'amanha_no_rio' else rio_antes_de_sair
    return snap, formato, fn(snap, False)


def agrupar_cenas(batidas):
    """Batida -> cena do telão. A primeira fala sem cartão vira a ABERTURA;
    falas sem cartão seguidas viram uma FRASE só. Formatos sem CTA usam a última
    batida (o fecho "Previsão RJ...") como CTA, para o card de seguir entrar."""
    tipos = []
    tem_cta = any(b['tipo'] == 'cta' for b in batidas)
    for i, b in enumerate(batidas):
        t = b['tipo']
        if i == 0 and t == 'nenhum':
            k = 'abertura'
        elif t == 'gancho':
            k = 'numero'
        elif t == 'resumo':
            k = 'quadro'
        elif t == 'alerta':
            k = 'alerta'
        elif t in ('cta', 'fecho') or (not tem_cta and i == len(batidas) - 1):
            k = 'cta'
        else:
            k = 'frase'
        tipos.append(k)
    cenas = []
    for i, k in enumerate(tipos):
        juntar = cenas and cenas[-1]['tipo'] == k and k in ('frase', 'abertura', 'cta')
        if juntar:
            cenas[-1]['batidas'].append(i)
        else:
            cenas.append({'tipo': k, 'batidas': [i]})
    for j, c in enumerate(cenas):
        c['id'] = f's{j}-{c["tipo"]}'
    return cenas


def momento_da_capa(cenas, cortes, dur):
    """Segundo do vídeo que vira a capa (miniatura da GRADE do perfil).

    O frame 0 do HyperFrames é só o cenário (tudo entra animado depois), e a
    grade ficou cheia de quadros sem temperatura. A capa passa a ser o QUADRO
    das cinco regiões já montado (~2,2 s após o início da cena, sem passar do
    corte seguinte). Sem quadro, usa a cena do número; sem ela, a abertura.
    """
    for tipo in ('quadro', 'numero', 'alerta'):
        for j, c in enumerate(cenas):
            if c['tipo'] != tipo:
                continue
            fim = cortes[j] - 0.15 if j < len(cortes) else dur - 0.2
            return round(max(c['ini'] + 0.6, min(c['ini'] + 2.2, fim)), 2)
    return round(min(1.5, dur / 2), 2)


def data_extenso(iso):
    d = dt.date.fromisoformat(iso)
    return f'{DIAS[d.weekday()]}, {d.day} DE {MESES[d.month - 1]}'


# ---------------------------------------------------------------- narração ---
def narrar(batidas, personagem, work):
    preset = PRESETS[personagem]
    raw = work / 'raw.wav'
    (work / 'roteiro.txt').write_text('\n'.join(b['fala'] for b in batidas), encoding='utf-8')
    run([sys.executable, '-m', PACKAGE + '.kokoro', work / 'roteiro.txt',
         '--voz', preset['voice'], '--speed', preset['speed'], '--gap', preset['gap'],
         '--out', raw, '--seg-json', work / 'segs.json'], cwd=RAIZ)
    return json.loads((work / 'segs.json').read_text())


def preparar(personagem, out, snapshot=None, formato='rio_antes_de_sair', topico=None):
    out = Path(out).resolve()
    work = out.parent / ('work_' + personagem)
    work.mkdir(parents=True, exist_ok=True)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    AUDIO.mkdir(parents=True, exist_ok=True)
    vendor = AQUI / 'assets' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    shutil.copy(RAIZ / 'video/node_modules/gsap/dist/gsap.min.js', vendor)

    if snapshot is None:
        snap, formato, batidas = demo_batidas(personagem)
        demo = True
    else:
        from src.previsao_rj.editorial.formats import prepare
        snap, demo = snapshot, False
        batidas = prepare(snapshot, formato, topic=topico)['beats']

    # 1) voz -> linha do tempo real (com o mesmo corte editorial do Manim)
    segs = narrar(batidas, personagem, work)
    if not demo:
        from src.previsao_rj.editorial.duracao import cortar_para_janela
        duracoes = [s['fim'] - s['ini'] for s in segs]
        restantes, cortadas = cortar_para_janela(batidas, duracoes)
        if cortadas:
            print(f'[duracao] {sum(duracoes):.1f}s excede a janela; cortando {len(cortadas)} batida(s)')
            batidas = restantes
            segs = narrar(batidas, personagem, work)
    gap = PRESETS[personagem]['gap']
    tempos = [(round(s['ini'], 3), round(max(s['ini'] + 0.2, s['fim'] - gap), 3)) for s in segs]
    dur = round(segs[-1]['fim'] + CAUDA, 2)

    narr = work / 'narracao.wav'
    run(['ffmpeg', '-y', '-v', 'error', '-i', work / 'raw.wav', '-af', FILTRO_VOZ,
         '-ar', '44100', '-ac', '1', narr])
    x, sr = ler_wav(narr)
    falta = int(dur * sr) - len(x)
    x = np.concatenate([x, np.zeros(max(0, falta), np.float32)])[:int(dur * sr)]
    gravar_wav(AUDIO / 'narracao.wav', x, sr)
    for i, b in enumerate(batidas):
        print(f'  [{b["tipo"]:8s}] {tempos[i][0]:5.2f}-{tempos[i][1]:5.2f}s  {b["fala"]}')

    # 2) lip sync pela energia do áudio (mesmo algoritmo do Manim)
    cues = gerar_cues(x / (np.abs(x).max() or 1), sr, fps=30)

    # 3) cenas, cortes e trilha
    cenas = agrupar_cenas(batidas)
    for c in cenas:
        c['ini'] = tempos[c['batidas'][0]][0]
    cortes = [round(max(0.05, c['ini'] - TRANS_DUR * 0.55), 3) for c in cenas[1:]]
    trans = [{'quadro': 'glitch', 'alerta': 'glitch', 'cta': 'flash-through-white'}
             .get(c['tipo'], 'whip-pan') for c in cenas[1:]]
    tr, sfx = trilha(dur, cortes, sr)
    gravar_wav(AUDIO / 'trilha.wav', tr, sr, estereo=True)
    gravar_wav(AUDIO / 'whoosh.wav', sfx, sr, estereo=True)

    # 4) palavras da legenda (karaokê) no tempo real de cada batida
    palavras = []
    for i, b in enumerate(batidas):
        for p in tempos_das_palavras(b['legenda'], *tempos[i]):
            p['b'] = i
            palavras.append(p)

    bloco = bloco_do_formato(snap, formato)
    locs = bloco.get('locations') or []
    from src.previsao_rj.editorial.cinco import cinco_regioes
    hora_alvo = os.environ.get('PREVISAO_RJ_HORA_ALVO') or ('18' if personagem == 'bia' else '6')
    agora = dt.datetime.now(ZoneInfo('America/Sao_Paulo'))
    data_iso = agora.date().isoformat() if not demo else (bloco.get('date') or agora.date().isoformat())
    pacote = {
        'dur': dur, 'personagem': personagem, 'formato': formato, 'demo': demo,
        'data': data_iso, 'data_ext': data_extenso(data_iso),
        'data_previsao': bloco.get('date') or data_iso,
        'hora': f'{int(hora_alvo):02d}:00',
        'ceu': ceu_do_dia(locs),
        'cidades': cinco_regioes(locs),
        'batidas': [dict(b, ini=tempos[i][0], fim=tempos[i][1]) for i, b in enumerate(batidas)],
        'cenas': cenas, 'cortes': cortes, 'transicoes': trans,
        'palavras': palavras,
        'capa_s': momento_da_capa(cenas, cortes, dur),
        'boca': [[c['start'], c['value']] for c in cues],
    }
    (BUILD / 'pacote.json').write_text(json.dumps(pacote, ensure_ascii=False, indent=1), encoding='utf-8')
    from compor import compor
    (AQUI / 'index.html').write_text(compor(pacote), encoding='utf-8')
    print(f'index.html pronto — {dur:.1f}s, {len(cenas)} cenas: '
          f'{" > ".join(c["tipo"] for c in cenas)} | transições: {", ".join(trans)}')
    return pacote, batidas, segs, work


# ---------------------------------------------------------------- render ---
def conferir(mp4, dur):
    data = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(mp4)]))
    vids = [s for s in data['streams'] if s['codec_type'] == 'video']
    auds = [s for s in data['streams'] if s['codec_type'] == 'audio']
    if len(vids) != 1 or not auds:
        raise ValueError('MP4 incompleto: vídeo ou áudio ausente')
    v = vids[0]
    if (v['width'], v['height'], v['avg_frame_rate']) != (1080, 1920, '30/1'):
        raise ValueError(f'Resolução/fps divergente: {v["width"]}x{v["height"]} {v["avg_frame_rate"]}')
    if abs(float(data['format']['duration']) - dur) > 0.15:
        raise ValueError(f'Duração divergente: {data["format"]["duration"]} vs {dur}')
    return data


def renderizar(out, pacote, qualidade='standard'):
    if not CLI.is_file():
        raise FileNotFoundError('Rode antes: npm ci --prefix video')
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1', DO_NOT_TRACK='1')
    for nome in ('ffmpeg', 'ffprobe'):
        if shutil.which(nome):
            env[f'HYPERFRAMES_{nome.upper()}_PATH'] = shutil.which(nome)
    run(['node', CLI, 'lint', AQUI], env=env, cwd=AQUI)
    out = Path(out).resolve()
    tmp = out.with_name(out.stem + '.rendering.mp4')
    run(['node', CLI, 'render', AQUI, '--output', tmp, '--quality', qualidade,
         '--workers', os.environ.get('PREVISAO_HF_WORKERS', '2')], env=env, cwd=AQUI)
    conferir(tmp, pacote['dur'])
    # Entrega igual à do pipeline aprovado: H.264 Main 4.0, 30 fps, AAC 48 kHz.
    final = out.with_name(out.stem + '.final.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-i', tmp,
         '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0', '-preset', 'medium',
         '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30',
         '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart', final])
    conferir(final, pacote['dur'])
    tmp.unlink()
    final.replace(out)
    return out


def entregar(personagem, out, pacote, batidas, segs, work):
    out = Path(out).resolve()
    run(['ffmpeg', '-y', '-v', 'error', '-i', out, '-vf', 'scale=720:1280',
         '-c:v', 'libx264', '-profile:v', 'main', '-crf', '24', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
         out.with_name(out.stem + '_preview_720p.mp4')])
    run([sys.executable, 'scripts/qa_video.py', out], cwd=RAIZ)
    run(['ffmpeg', '-y', '-v', 'error', '-ss', '2', '-i', out, '-frames:v', '1', out.with_suffix('.png')])
    # Capa da grade: CAPA.jpg + capa_ms.txt na mesma pasta do MP4.
    capa_s = pacote.get('capa_s') or 2
    capa = out.with_name('CAPA.jpg')
    run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{capa_s:.2f}', '-i', out,
         '-frames:v', '1', '-q:v', '2', capa])
    if not capa.is_file() or capa.stat().st_size < 10_000:
        raise RuntimeError('capa da grade não foi gerada')
    out.with_name('capa_ms.txt').write_text(str(int(capa_s * 1000)))
    print(f'capa da grade: {capa_s:.2f}s -> {capa}')
    manifest = {'character': personagem, 'preset': PRESETS[personagem], 'filter': FILTRO_VOZ,
                'estilo': 'hyperframes-estudio', 'motor_video': 'hyperframes',
                'hyperframes_version': VERSAO_HF, 'demo': pacote['demo'],
                'formato': pacote['formato'], 'ceu': pacote['ceu'],
                'cenas': [c['tipo'] for c in pacote['cenas']],
                'segments': segs, 'video': out.name, 'publication': False}
    out.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy(BUILD / 'pacote.json', work / 'pacote_hyperframes.json')


def main():
    from src.previsao_rj.editorial.formats import TITLES
    ap = argparse.ArgumentParser()
    ap.add_argument('--personagem', choices=('bira', 'bia'), default='bira')
    ap.add_argument('--out', required=True)
    ap.add_argument('--format', choices=TITLES, default='rio_antes_de_sair')
    ap.add_argument('--topico', default=None)
    ap.add_argument('--qualidade', default='standard', choices=['draft', 'standard', 'high'])
    ap.add_argument('--so-html', action='store_true', help='só gera o index.html (sem render)')
    fonte = ap.add_mutually_exclusive_group(required=True)
    fonte.add_argument('--demo', action='store_true')
    fonte.add_argument('--snapshot')
    a = ap.parse_args()
    snapshot = json.loads(Path(a.snapshot).read_text()) if a.snapshot else None

    if os.environ.get('PREVISAO_RJ_MOTOR', 'hyperframes').strip().lower() == 'manim':
        from src.previsao_rj.render.characters.pipeline import render
        print('PREVISAO_RJ_MOTOR=manim — usando o pipeline Manim (reserva)')
        render(a.personagem, a.out, snapshot, a.format, a.topico or None)
        return

    Path(a.out).resolve().parent.mkdir(parents=True, exist_ok=True)
    pacote, batidas, segs, work = preparar(a.personagem, a.out, snapshot, a.format, a.topico or None)
    if a.so_html:
        return
    renderizar(a.out, pacote, a.qualidade)
    entregar(a.personagem, a.out, pacote, batidas, segs, work)
    print(f'ok: {a.out}')


if __name__ == '__main__':
    main()

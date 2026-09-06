"""Render isolado com os desenhos e presets de voz do Ranzinza/Dona Maria."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = 'src.previsao_rj.render.characters'
PRESETS = {
    'ranzinza': {'voice': 'pm_alex', 'pitch': 0.88, 'speed': 0.95, 'gap': 0.30},
    'maria': {'voice': 'pf_dora', 'pitch': 0.94, 'speed': 0.95, 'gap': 0.30},
}
FILTER = ('asetrate=44100*{pitch},aresample=44100,atempo={inv:.5f},'
          'vibrato=f=5.5:d=0.09,highpass=f=90,'
          'acompressor=threshold=-18dB:ratio=3:attack=8:release=180,volume=1.15')


def beat(text, kind='nenhum', **data):
    return {'fala': text, 'legenda': text, 'tipo': kind, 'dados': data}


def demo_beats(character):
    if character == 'maria':
        return [
            beat('Olha só! A Dona Maria chegou ao Previsão Rio.'),
            beat('Eu já trouxe os óculos e o meu avental de flores.', acao='apontar'),
            beat('Até o velho veio junto. Só espero que ele reclame menos!'),
        ]
    return [
        beat('Ora, vejam só! O Ranzinza chegou ao Previsão Rio.'),
        beat('Trouxe a minha bengala, os meus óculos e a minha paciência.'),
        beat('Paciência pouca, viu? Mas a previsão eu conto direitinho!'),
    ]


def snapshot_beats(snapshot):
    locs = snapshot['forecast']['today']['locations']
    if not locs:
        raise ValueError('Snapshot sem localidades')
    rows = []
    for loc in locs[:3]:
        city = {'nome': loc['name'], 'min': round(loc['min_c']),
                'max': round(loc['max_c']), 'cond': 'nublado'}
        rows.append(beat(f"Em {city['nome']}, mínima de {city['min']} e máxima de {city['max']} graus.",
                         'cidade', cidade=city))
    return [beat('Antes de sair, confira como a temperatura muda pela região.')] + rows + [
        beat('Veja a previsão atualizada no Previsão Rio e compartilhe com quem sai com você.')]


def run(cmd, **kwargs):
    subprocess.run([str(x) for x in cmd], check=True, cwd=ROOT, **kwargs)


def render(character, destination, snapshot=None):
    preset = PRESETS[character]
    out = Path(destination).resolve()
    work = out.parent / ('work_' + character)
    work.mkdir(parents=True, exist_ok=True)
    beats = snapshot_beats(snapshot) if snapshot is not None else demo_beats(character)
    (work / 'roteiro.txt').write_text('\n'.join(b['fala'] for b in beats), encoding='utf-8')
    raw, narration = work / 'raw.wav', work / 'narracao.wav'
    run([sys.executable, '-m', PACKAGE + '.kokoro', work / 'roteiro.txt',
         '--voz', preset['voice'], '--speed', preset['speed'], '--gap', preset['gap'],
         '--out', raw, '--seg-json', work / 'segs.json'])
    audio_filter = FILTER.format(pitch=preset['pitch'], inv=1 / preset['pitch'])
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', audio_filter,
         '-ar', '44100', '-ac', '1', narration])
    run([sys.executable, '-m', PACKAGE + '.amplitude', narration, work / 'lip_full.json', '--fps', '22'])
    segments = json.loads((work / 'segs.json').read_text())
    content = {'batidas': beats, 'personagem': character,
               'cenario': 'entardecer' if character == 'maria' else 'sol',
               'cenario_tipo': 'quintal' if character == 'maria' else 'varanda',
               'calor': False, 'vento_visual': 0.7, 'demo': snapshot is None,
               'destaque': 'PREVISÃO RJ', 'destaque_rotulo': 'TESTE DE PERSONAGEM' if snapshot is None else 'TEMPERATURAS'}
    (work / 'conteudo.json').write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    env = dict(os.environ, PREVISAO_RJ_TRAB=str(work),
               PREVISAO_RJ_LIP_JSON=str(work / 'lip_full.json'), PYTHONPATH=str(ROOT))
    run([sys.executable, '-m', 'manim', '-qm', '--fps', '30', '--disable_caching',
         '--media_dir', work / 'media', Path(__file__).with_name('scene.py'), 'Piloto'], env=env)
    candidates = list((work / 'media' / 'videos').rglob('Piloto.mp4'))
    if len(candidates) != 1:
        raise RuntimeError(f'Esperado um render, encontrados {len(candidates)}')
    run(['ffmpeg', '-y', '-v', 'error', '-i', candidates[0], '-i', narration,
         '-c:v', 'libx264', '-crf', '22', '-preset', 'medium', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out])
    run([sys.executable, 'scripts/qa_video.py', out])
    run(['ffmpeg', '-y', '-v', 'error', '-ss', '2', '-i', out, '-frames:v', '1', out.with_suffix('.png')])
    manifest = {'character': character, 'preset': preset, 'filter': audio_filter,
                'demo': snapshot is None, 'segments': segments,
                'source_commit': '90e2ab5e040695821437f711fed25d2875161557',
                'video': out.name, 'publication': False}
    out.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--personagem', choices=PRESETS, default='ranzinza')
    parser.add_argument('--out', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true')
    source.add_argument('--snapshot')
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text()) if args.snapshot else None
    render(args.personagem, args.out, snapshot)


if __name__ == '__main__':
    main()

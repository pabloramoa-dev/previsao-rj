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
    'bira': {'voice': 'pm_alex', 'pitch': 1.0, 'speed': 1.04, 'gap': 0.22},
    'bia': {'voice': 'pf_dora', 'pitch': 1.0, 'speed': 1.02, 'gap': 0.24},
    'ranzinza': {'voice': 'pm_alex', 'pitch': 0.88, 'speed': 0.95, 'gap': 0.30},
    'maria': {'voice': 'pf_dora', 'pitch': 0.94, 'speed': 0.95, 'gap': 0.30},
}
FILTER = ('asetrate=44100*{pitch},aresample=44100,atempo={inv:.5f},'
          'vibrato=f=5.5:d=0.09,highpass=f=90,'
          'acompressor=threshold=-18dB:ratio=3:attack=8:release=180,volume=1.15')


def beat(text, kind='nenhum', **data):
    return {'fala': text, 'legenda': text, 'tipo': kind, 'dados': data}


def demo_beats(character):
    if character in {'bira', 'bia'}:
        name = 'Bira do Tempo' if character == 'bira' else 'Bia da Orla'
        return [beat(f'Eu sou {name}, do Previsão Rio. Vamos olhar o tempo com calma?'),
                beat('Entre a orla e a Baixada, a previsão pode mudar bastante.', acao='apontar'),
                beat('Com os dados de cada região, fica mais fácil decidir o seu dia.'),
                beat('Este é um teste de imagem e voz. A Nuvem Rio veio conferir também!')]

    if character == 'maria':
        return [
            beat('Olha só! A Dona Maria chegou ao Previsão Rio.'),
            beat('Eu já trouxe os óculos e o meu avental de flores.', acao='apontar'),
            beat('Até o velho veio junto. Só espero que ele reclame menos!'),
            beat('Agora me conta: você reconheceu o meu jeitinho e a minha voz?'),
        ]
    return [
        beat('Ora, vejam só! O Ranzinza chegou ao Previsão Rio.'),
        beat('Trouxe a minha bengala, os meus óculos e a minha paciência.'),
        beat('Paciência pouca, viu? Mas a previsão eu conto direitinho!'),
        beat('A Dona Maria também está por aqui. Já chegou querendo mandar em tudo!'),
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


def estilo_vox() -> bool:
    """Colagem de papel (Vox) é o padrão. PREVISAO_RJ_ESTILO=classico desliga."""
    return os.environ.get('PREVISAO_RJ_ESTILO', 'vox').strip().lower() != 'classico'


def run(cmd, **kwargs):
    subprocess.run([str(x) for x in cmd], check=True, cwd=ROOT, **kwargs)


def render(character, destination, snapshot=None, format="rio_antes_de_sair", topic=None):
    preset = PRESETS[character]
    out = Path(destination).resolve()
    work = out.parent / ('work_' + character)
    work.mkdir(parents=True, exist_ok=True)
    from ...editorial.formats import prepare
    prepared = prepare(snapshot, format, topic=topic) if snapshot is not None else None
    beats = prepared["beats"] if prepared else demo_beats(character)
    raw, narration = work / 'raw.wav', work / 'narracao.wav'

    def narrar(batidas):
        (work / 'roteiro.txt').write_text('\n'.join(b['fala'] for b in batidas), encoding='utf-8')
        run([sys.executable, '-m', PACKAGE + '.kokoro', work / 'roteiro.txt',
             '--voz', preset['voice'], '--speed', preset['speed'], '--gap', preset['gap'],
             '--out', raw, '--seg-json', work / 'segs.json'])
        return json.loads((work / 'segs.json').read_text())

    segments = narrar(beats)

    # Dia cheio rende roteiro longo, e roteiro longo o QA recusa (foi o que
    # aconteceu em 15/09/2026: 43,2 s contra um teto de 40). Quem decide o que
    # sai é o criterio editorial de `duracao`, nao o acaso do render.
    if snapshot is not None:
        from ...editorial.duracao import cortar_para_janela
        duracoes = [s['fim'] - s['ini'] for s in segments]
        restantes, cortadas = cortar_para_janela(beats, duracoes)
        if cortadas:
            print(f'[duracao] {sum(duracoes):.1f}s excede a janela editorial; '
                  f'cortando {len(cortadas)} batida(s):')
            for i in cortadas:
                print(f'  - [{beats[i].get("tipo")}] {beats[i]["fala"]}')
            beats = restantes
            segments = narrar(beats)
            print(f'[duracao] narracao final: {segments[-1]["fim"]:.1f}s '
                  f'em {len(beats)} batidas')

    audio_filter = ('highpass=f=80,acompressor=threshold=-18dB:ratio=2:attack=8:release=180,volume=1.1'
                    if character in {'bira', 'bia'} else FILTER.format(pitch=preset['pitch'], inv=1 / preset['pitch']))
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', audio_filter,
         '-ar', '44100', '-ac', '1', narration])
    run([sys.executable, '-m', PACKAGE + '.amplitude', narration, work / 'lip_full.json', '--fps', '22'])
    content = {'batidas': beats, 'personagem': character,
               'cenario': 'entardecer' if character == 'maria' else 'sol',
               'cenario_tipo': 'quintal' if character == 'maria' else 'varanda',
               'calor': False, 'vento_visual': 0.7, 'demo': snapshot is None,
               'destaque': 'PREVISÃO RJ',
               'destaque_rotulo': ('TESTE DE PERSONAGEM' if snapshot is None
                                   else 'AMANHÃ' if format == 'amanha_no_rio' else 'TEMPERATURAS')}
    (work / 'conteudo.json').write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    env = dict(os.environ, PREVISAO_RJ_TRAB=str(work),
               PREVISAO_RJ_LIP_JSON=str(work / 'lip_full.json'), PYTHONPATH=str(ROOT))
    run([sys.executable, '-m', 'manim', '-qm', '--fps', '30', '--disable_caching',
         '--media_dir', work / 'media', Path(__file__).with_name('scene.py'), 'Piloto'], env=env)
    candidates = list((work / 'media' / 'videos').rglob('Piloto.mp4'))
    if len(candidates) != 1:
        raise RuntimeError(f'Esperado um render, encontrados {len(candidates)}')
    vox = estilo_vox()
    if vox:
        # Colagem: grão de papel sobre o vídeo mudo, voz masterizada por ganho
        # fixo + limitador, e entrega H.264 Main / Level 4.0 a 30 fps.
        from . import vox_papel as VX
        mudo = VX.aplicar_textura(candidates[0], work / 'mudo_papel.mp4')
        master = VX.masterizar(narration, work / 'narracao_master.wav')
        run(['ffmpeg', '-y', '-v', 'error', '-i', mudo, '-i', master,
             '-map', '0:v', '-map', '1:a',
             '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0', '-preset', 'medium',
             '-crf', '22', '-pix_fmt', 'yuv420p', '-r', '30',
             '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
             '-movflags', '+faststart', '-shortest', out])
        run(['ffmpeg', '-y', '-v', 'error', '-i', out, '-vf', 'scale=720:1280',
             '-c:v', 'libx264', '-profile:v', 'main', '-crf', '24', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
             out.with_name(out.stem + '_preview_720p.mp4')])
    else:
        run(['ffmpeg', '-y', '-v', 'error', '-i', candidates[0], '-i', narration,
             '-c:v', 'libx264', '-crf', '22', '-preset', 'medium', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out])
    run([sys.executable, 'scripts/qa_video.py', out])
    run(['ffmpeg', '-y', '-v', 'error', '-ss', '2', '-i', out, '-frames:v', '1', out.with_suffix('.png')])
    manifest = {'character': character, 'preset': preset, 'filter': audio_filter,
                'estilo': 'vox' if vox else 'classico',
                'demo': snapshot is None, 'segments': segments,
                'source_commit': '90e2ab5e040695821437f711fed25d2875161557',
                'video': out.name, 'publication': False}
    out.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--personagem', choices=PRESETS, default='bira')
    parser.add_argument('--out', required=True)
    from ...editorial.formats import TITLES
    parser.add_argument('--format', choices=TITLES, default='rio_antes_de_sair')
    parser.add_argument('--topico', default=None,
                        help='tópico da pauta (output/pauta.json); vazio = o de maior nota')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true')
    source.add_argument('--snapshot')
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text()) if args.snapshot else None
    render(args.personagem, args.out, snapshot, args.format, args.topico or None)


if __name__ == '__main__':
    main()


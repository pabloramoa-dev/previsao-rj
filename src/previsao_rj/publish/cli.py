"""CLI de publicacao — Plano Mestre v1.1, secoes 13.4 e 18.

Com `--queue`, o publicador deixa de ser cego: reivindica o item na fila antes
de falar com a Meta e grava o resultado nela depois. E isso que arma os vetos
de duplicata e de gancho repetido do motor editorial, que leem `status`
'published' e `published_at`.

Sem `--queue` o comportamento antigo continua valendo, para nao quebrar o
workflow manual que ja roda.
"""
from __future__ import annotations

import argparse

from . import state
from .instagram import (already_published_caption, caption_hash, create_reel,
                        publish, verify_destination, wait_ready)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--video-url', required=True)
    parser.add_argument('--caption-file', required=True)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--queue', help='fila do motor editorial (JSON) a atualizar')
    parser.add_argument('--dedupe-key', help='item da fila a publicar; sem isso, o melhor pronto')
    args = parser.parse_args()

    caption = open(args.caption_file, encoding='utf-8').read().strip()
    if '@previsaorj' not in caption.casefold():
        raise SystemExit('marca @previsaorj ausente: publicação bloqueada')
    print('caption_hash=', caption_hash(caption))

    key = args.dedupe_key
    if args.queue and not key:
        candidate = state.next_ready(args.queue)
        if candidate is None:
            raise SystemExit('fila sem item pronto e dentro da validade: nada a publicar')
        key = candidate['dedupe_key']
        print('item_escolhido=', key, candidate.get('format'), candidate.get('topic'))

    destination = verify_destination()
    print('destino_verificado=', destination.get('username'))

    if not args.publish:
        print('DRY-RUN: nenhum container foi criado; fila intacta')
        return

    if already_published_caption(caption):
        raise SystemExit('DUPLICATA BLOQUEADA: legenda equivalente já publicada')

    if args.queue:
        state.claim(args.queue, key)
        print('item_reivindicado=', key)

    # Antes de media_publish nada foi ao ar: falha aqui devolve o item para a fila.
    try:
        container = create_reel(args.video_url, caption)
        wait_ready(container)
    except BaseException as exc:
        if args.queue:
            state.release(args.queue, key, f'falha antes de publicar: {type(exc).__name__}')
        raise

    # Daqui em diante a midia pode existir: falha vira 'unknown', nunca 'ready'.
    try:
        media_id = publish(container)
    except BaseException as exc:
        if args.queue:
            state.mark_unknown(args.queue, key,
                               f'falha durante media_publish: {type(exc).__name__}: {exc}')
        raise

    print('media_id=', media_id)
    if args.queue:
        state.commit(args.queue, key, media_id)
        print('fila_atualizada=', key, '-> published')


if __name__ == '__main__':
    main()

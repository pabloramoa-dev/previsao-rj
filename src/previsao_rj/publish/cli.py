from __future__ import annotations
import argparse, json, os
from .instagram import verify_destination, create_reel, wait_ready, publish, caption_hash, already_published_caption


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--video-url', required=True)
    p.add_argument('--caption-file', required=True)
    p.add_argument('--publish', action='store_true')
    args=p.parse_args()
    cap=open(args.caption_file,encoding='utf-8').read().strip()
    if '@previsaorj' not in cap.casefold():
        raise SystemExit('marca @previsaorj ausente: publicação bloqueada')
    print('caption_hash=', caption_hash(cap))
    dest=verify_destination()
    print('destino_verificado=', dest.get('username'))
    if not args.publish:
        print('DRY-RUN: nenhum container foi criado')
        return
    if already_published_caption(cap):
        raise SystemExit('DUPLICATA BLOQUEADA: legenda equivalente já publicada')
    cid=create_reel(args.video_url, cap)
    wait_ready(cid)
    mid=publish(cid)
    print('media_id=', mid)
if __name__=='__main__': main()

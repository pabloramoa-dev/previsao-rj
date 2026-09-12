"""Gera decisao e fila sem publicar.

A fila e o ESTADO PERSISTENTE do publicador (secao 13.4): fica versionada em
`data/editorial_queue.json` e sobrevive entre execucoes. O historico que arma
os vetos de duplicata e de gancho repetido sai da propria fila — do que foi
marcado como `published` pelo publicador — em vez de um arquivo paralelo que
ninguem escrevia.
"""
import argparse
import json
from pathlib import Path

from src.previsao_rj.editorial.engine import evaluate, queue_file
from src.previsao_rj.publish import state

QUEUE_DEFAULT = 'data/editorial_queue.json'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('--out', default=QUEUE_DEFAULT, help='fila persistente a atualizar')
    p.add_argument('--history', default=None,
                   help='historico externo adicional (compatibilidade); o padrao e a propria fila')
    args = p.parse_args()

    history = state.history(args.out)
    if args.history and Path(args.history).exists():
        history = history + json.loads(Path(args.history).read_text(encoding='utf-8'))

    candidates = evaluate(json.loads(Path(args.snapshot).read_text(encoding='utf-8')), history)
    queue_file(args.out, candidates)

    print(f'historico considerado: {len(history)} publicacoes')
    for c in candidates:
        print(c['format'], c['topic'], c['total'], c['status'], ', '.join(c['vetoes']))


if __name__ == '__main__':
    main()

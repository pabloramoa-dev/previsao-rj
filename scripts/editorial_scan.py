"""Gera decisão e fila sem publicar."""
import argparse
import json
from pathlib import Path
from src.previsao_rj.editorial.engine import evaluate, queue_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('--history', default='data/editorial_history.json')
    p.add_argument('--out', default='output/editorial_queue.json')
    args = p.parse_args()
    history = json.loads(Path(args.history).read_text()) if Path(args.history).exists() else []
    candidates = evaluate(json.loads(Path(args.snapshot).read_text()), history)
    queue_file(args.out, candidates)
    for c in candidates:
        print(c['format'], c['topic'], c['total'], c['status'], ', '.join(c['vetoes']))


if __name__ == '__main__': main()

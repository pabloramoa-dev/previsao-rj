"""Monta a legenda do Reel.

Com `--pauta`, a legenda segue o item que o `escolher_pauta` selecionou — o
mesmo que o render desenhou e o publicador vai marcar como publicado. Sem ele,
o texto geral do dia continua valendo.
"""
import argparse
import json
from pathlib import Path

from src.previsao_rj.publish.caption import build_caption


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('saida')
    p.add_argument('--pauta', default=None,
                   help='JSON do item da fila escolhido (output/pauta.json)')
    args = p.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
    item = None
    if args.pauta and Path(args.pauta).exists():
        item = json.loads(Path(args.pauta).read_text(encoding='utf-8'))

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(build_caption(snapshot, item), encoding='utf-8')
    print(saida)


if __name__ == '__main__':
    main()

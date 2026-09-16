"""Escolhe UMA pauta e faz video, legenda e fila obedecerem a ela.

Ate 13/09/2026 os tres decidiam separado: o render usava o formato default
(`rio_antes_de_sair`) e o personagem marcado na mao, a legenda saia so do
snapshot e o publicador reivindicava o melhor item da fila. No primeiro Reel
real isso gravou como publicada uma pauta `fim_de_semana` da Bia enquanto o
video no ar era outro. O historico editorial ficou registrando o que ninguem
viu, e e desse historico que saem os vetos de duplicata e de gancho repetido.

Este script e o ponto unico de decisao. Ele roda depois do `editorial_scan` e
antes do render: le a fila, escolhe o melhor item pronto e dentro da validade,
grava o item em JSON e devolve formato, personagem e dedupe_key para o
workflow. O render recebe `--format` e `--personagem` daqui, a legenda recebe
`--pauta` daqui, e o publicador recebe `--dedupe-key` daqui.

Com `--exigir-inedito-hoje`, tambem e a trava do Reel diario: se a fila ja
registra publicacao com a data local de hoje, a execucao sai por `seguir=nao`
em vez de publicar duas vezes. E o que permite agendar varias tentativas de
cron sabendo que so a primeira que realmente disparar vai ao ar.
"""
import argparse
import json
import os
from pathlib import Path

from src.previsao_rj.collectors.base import now
from src.previsao_rj.publish import state

QUEUE_DEFAULT = 'data/editorial_queue.json'


def anotar(**saidas: str) -> None:
    """Escreve no $GITHUB_OUTPUT quando existe; sempre mostra no log."""
    destino = os.environ.get('GITHUB_OUTPUT')
    for chave, valor in saidas.items():
        print(f'{chave}={valor}')
    if destino:
        with open(destino, 'a', encoding='utf-8') as arquivo:
            for chave, valor in saidas.items():
                arquivo.write(f'{chave}={valor}\n')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--queue', default=QUEUE_DEFAULT)
    p.add_argument('--out', default='output/pauta.json')
    p.add_argument('--exigir-inedito-hoje', action='store_true',
                   help='sai por seguir=nao se a fila ja registra publicacao de hoje')
    p.add_argument('--turno', choices=('manha', 'noite'), default=None,
                   help='manha = previsao do dia (Bira); noite = previsao de amanha (Bia)')
    p.add_argument('--exigir-pauta', action='store_true',
                   help='falha (em vez de seguir=nao) quando nao ha item pronto')
    args = p.parse_args()

    hoje = now().date().isoformat()

    if args.exigir_inedito_hoje:
        publicado = state.published_on(args.queue, hoje, turno=args.turno)
        if publicado is not None:
            print(f'Ja publicado hoje ({hoje}, turno {args.turno or "qualquer"}): '
                  f'{publicado.get("format")} '
                  f'{publicado.get("topic")} media_id={publicado.get("media_id")}')
            anotar(seguir='nao', motivo='ja_publicado_hoje')
            return

    item = state.next_ready(args.queue, turno=args.turno)
    if item is None:
        print(f'Fila sem item pronto e dentro da validade (turno {args.turno or "qualquer"}).')
        if args.exigir_pauta:
            raise SystemExit('nenhuma pauta publicavel: execucao interrompida')
        anotar(seguir='nao', motivo='sem_pauta_pronta')
        return

    destino = Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Pauta escolhida: {item["format"]} / {item.get("topic")} '
          f'total={item.get("total")} confianca={item.get("confidence")}')
    anotar(seguir='sim',
           formato=item['format'],
           personagem=item.get('character', 'bira'),
           dedupe_key=item['dedupe_key'],
           topico=str(item.get('topic', '')),
           pauta=str(destino))


if __name__ == '__main__':
    main()

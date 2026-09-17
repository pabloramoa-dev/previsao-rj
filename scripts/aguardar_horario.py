"""Relógio do Reel diário: preparar antes, publicar na hora certa.

O Reel de cada turno segue três marcos no horário de Brasília:

    PREPARO = ALVO - antecedência   coleta a previsão, escolhe a pauta, renderiza
    ALVO                            publica (o vídeo já está pronto e guardado)
    PRAZO                           disparo automático que chegar depois disso
                                    não publica mais (a previsão da manhã não vai
                                    ao ar de tarde, nem a de amanhã de madrugada)

Quem dispara o workflow cedo (gatilho externo ~45 min antes, ou um cron de
reserva de madrugada) espera aqui até o PREPARO, prepara o Reel e espera de
novo até o ALVO. Quem dispara atrasado não espera nada e segue direto.

Só biblioteca padrão: o job `trava` roda sem instalar dependências.

Uso:
    python -m scripts.aguardar_horario preparar --alvo 06:00 --antes 40
    python -m scripts.aguardar_horario publicar --alvo 06:00
    python -m scripts.aguardar_horario prazo --prazo 10:00      # sai 0/1
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))


def agora() -> datetime:
    return datetime.now(BRT)


def momento(hhmm: str, referencia: datetime) -> datetime:
    """Hoje (na data local da referência) às HH:MM de Brasília."""
    hora, minuto = (int(p) for p in hhmm.strip().split(':'))
    return referencia.astimezone(BRT).replace(hour=hora, minute=minuto,
                                              second=0, microsecond=0)


def segundos_de_espera(alvo: str, antes_min: int = 0,
                       referencia: datetime | None = None) -> int:
    """Quanto falta até ALVO - antes_min. Zero se o momento já passou."""
    referencia = referencia or agora()
    marco = momento(alvo, referencia) - timedelta(minutes=antes_min)
    return max(0, int((marco - referencia).total_seconds()))


def dentro_do_prazo(prazo: str, referencia: datetime | None = None) -> bool:
    referencia = referencia or agora()
    return referencia <= momento(prazo, referencia)


def esperar(alvo: str, antes_min: int, rotulo: str) -> None:
    falta = segundos_de_espera(alvo, antes_min)
    marco = momento(alvo, agora()) - timedelta(minutes=antes_min)
    if falta <= 0:
        print(f'{rotulo}: {marco:%H:%M} já passou (agora {agora():%H:%M}); seguindo.')
        return
    print(f'{rotulo}: aguardando {falta // 60} min, até {marco:%H:%M} de Brasília.', flush=True)
    time.sleep(falta)
    print(f'{rotulo}: {agora():%H:%M:%S}, seguindo.')


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='acao', required=True)
    a = sub.add_parser('preparar')
    a.add_argument('--alvo', required=True)
    a.add_argument('--antes', type=int, default=40)
    b = sub.add_parser('publicar')
    b.add_argument('--alvo', required=True)
    c = sub.add_parser('prazo')
    c.add_argument('--prazo', required=True)
    args = p.parse_args()
    if args.acao == 'preparar':
        esperar(args.alvo, args.antes, 'preparo')
    elif args.acao == 'publicar':
        esperar(args.alvo, 0, 'publicação')
    else:
        ok = dentro_do_prazo(args.prazo)
        print(f'agora {agora():%H:%M}, prazo {args.prazo}: '
              f'{"dentro" if ok else "FORA"} do prazo')
        raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()

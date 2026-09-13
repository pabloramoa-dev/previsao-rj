# -*- coding: utf-8 -*-
"""Radar colaborativo: o que os seguidores estao vendo agora, por zona.

O estado vive em memoria do processo. Isso e uma escolha, nao um esquecimento:
o relato so vale por poucas horas, e um reinicio do servico custa, no pior
caso, o resumo de uma janela. Se um Postgres for plugado depois, basta definir
DATABASE_URL e instalar psycopg — a gravacao passa a ir para o banco e a
leitura continua igual, sem tocar no webhook.

Nunca guardamos o ID do usuario do Instagram. O que entra na tabela e um hash
com sal (RADAR_HASH_SALT), que serve para nao contar a mesma pessoa duas vezes
e nao serve para saber quem ela e.
"""
from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timedelta, timezone
import hashlib
import os
import threading

_MEMORIA: deque = deque(maxlen=2000)
_EVENTOS: deque = deque(maxlen=5000)
_EVENTOS_SET: set[str] = set()
_CONTEXTOS: dict[str, tuple[datetime, str, str, str]] = {}
_TRAVA = threading.Lock()
_URL = os.environ.get("DATABASE_URL", "")
_DB_OK = False

JANELA_PADRAO_H = 3
CONTEXTO_MINUTOS = 15


def _hash(uid: str) -> str:
    sal = os.environ.get("RADAR_HASH_SALT", "previsaorj")
    return hashlib.sha256(f"{sal}:{uid}".encode()).hexdigest()[:20]


def _conectar():
    if not _URL:
        return None
    import psycopg  # importado so quando ha banco configurado
    return psycopg.connect(_URL, connect_timeout=5)


def inicializar() -> bool:
    """Cria as tabelas se houver banco. Sem banco, segue em memoria."""
    global _DB_OK
    if not _URL or _DB_OK:
        return _DB_OK
    try:
        with _conectar() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS relatos (
                id BIGSERIAL PRIMARY KEY,
                message_id TEXT UNIQUE NOT NULL,
                user_hash TEXT NOT NULL,
                zona TEXT NOT NULL,
                local TEXT NOT NULL,
                condicao TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS relatos_zona_data "
                        "ON relatos (zona, created_at DESC)")
        _DB_OK = True
    except Exception as exc:
        _DB_OK = False
        print(f"[radar] banco indisponivel; seguindo em memoria: {exc}")
    return _DB_OK


def marcar_evento(event_id: str) -> bool:
    """True na primeira vez que este evento aparece. A Meta reenvia webhook."""
    with _TRAVA:
        if event_id in _EVENTOS_SET:
            return False
        if len(_EVENTOS) == _EVENTOS.maxlen:
            _EVENTOS_SET.discard(_EVENTOS[0])
        _EVENTOS.append(event_id)
        _EVENTOS_SET.add(event_id)
        return True


def registrar(message_id: str, uid: str, zona: str, local: str,
              condicao: str) -> bool:
    """Registra um relato uma unica vez por mensagem."""
    if not marcar_evento(f"relato:{message_id}"):
        return False
    agora = datetime.now(timezone.utc)
    with _TRAVA:
        _MEMORIA.append({"zona": zona, "local": local, "condicao": condicao,
                         "created_at": agora, "user_hash": _hash(uid)})
    if inicializar():
        try:
            with _conectar() as con:
                con.execute(
                    """INSERT INTO relatos(message_id,user_hash,zona,local,condicao)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT(message_id) DO NOTHING""",
                    (message_id, _hash(uid), zona, local, condicao))
        except Exception as exc:
            print(f"[radar] falha ao gravar no banco: {exc}")
    return True


def guardar_contexto(uid: str, zona: str, local: str, rotulo: str) -> None:
    """Lembra o ultimo local respondido, para entender a resposta curta seguinte."""
    expira = datetime.now(timezone.utc) + timedelta(minutes=CONTEXTO_MINUTOS)
    with _TRAVA:
        _CONTEXTOS[_hash(uid)] = (expira, zona, local, rotulo)


def obter_contexto(uid: str) -> tuple[str, str, str] | None:
    agora = datetime.now(timezone.utc)
    with _TRAVA:
        item = _CONTEXTOS.get(_hash(uid))
        if item and item[0] > agora:
            return item[1], item[2], item[3]
    return None


def resumo(zona_nome: str | None = None, horas: int = JANELA_PADRAO_H) -> str:
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    with _TRAVA:
        recentes = [r for r in _MEMORIA
                    if r["created_at"] >= desde
                    and (not zona_nome or r["zona"] == zona_nome)]

    titulo = f"📡 Radar dos seguidores — ultimas {horas}h"
    if zona_nome:
        titulo += f" na {zona_nome}"
    if not recentes:
        return (titulo + "\nAinda nao ha relato nessa janela. "
                "Manda o teu bairro + CHUVA, SOL, VENTO ou NUBLADO "
                "que voce entra no radar.")

    chave = (lambda r: (r["local"], r["condicao"])) if zona_nome else (
        lambda r: (r["zona"], r["condicao"]))
    itens = Counter(chave(r) for r in recentes).most_common(6)
    corpo = "\n".join(f"• {lugar}: {cond} ({n})" for (lugar, cond), n in itens)
    pessoas = len({r["user_hash"] for r in recentes})
    return (f"{titulo}\n{corpo}\n"
            f"({len(recentes)} relatos de {pessoas} pessoas)\n"
            "Relato da comunidade, nao e boletim oficial.")


def estado() -> dict:
    return {"banco": "ok" if _DB_OK else ("configurado" if _URL else "memoria"),
            "relatos_em_memoria": len(_MEMORIA),
            "contextos_ativos": len(_CONTEXTOS)}

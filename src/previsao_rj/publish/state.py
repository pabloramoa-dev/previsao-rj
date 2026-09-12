"""Estado persistente do publicador — Plano Mestre v1.1, secoes 13.4 e 18.

A fila escrita por `editorial.engine.queue_file` e a unica fonte de verdade
sobre o que ja foi ao ar. Ate aqui ela so era escrita pelo motor editorial: o
publicador publicava e nao contava para ninguem, entao `evaluate()` nunca via
historico e os vetos de duplicata e de gancho repetido nasciam desarmados.

Este modulo fecha o ciclo:

    ready --claim--> publishing --commit--> published
                          |
                          +-- release ------> ready     (falha ANTES de existir midia)
                          +-- mark_unknown -> unknown   (falha DEPOIS de poder existir)

Regra dura: nada volta para `ready` depois que a Meta pode ter aceitado a
publicacao. Na duvida o item vira `unknown` e espera conferencia humana — e o
mesmo criterio que `queue_file` ja usava para nunca sobrescrever `published`,
`publishing` e `unknown`.

Toda escrita e atomica (arquivo temporario + replace) para que uma interrupcao
no meio do caminho nao deixe a fila truncada.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..collectors.base import iso, now
from ..editorial.engine import stamp

CLAIMABLE = {"ready"}
FINAL = {"published"}
NEEDS_REVIEW = {"unknown"}


class QueueError(RuntimeError):
    """Erro de estado da fila: o item nao pode sofrer a transicao pedida.

    `persist=True` diz que a mudanca feita antes da recusa deve ser gravada —
    e o caso do item vencido, que precisa ficar registrado como `expired` em
    vez de continuar aparecendo como `ready` na proxima execucao.
    """

    def __init__(self, message: str, *, persist: bool = False) -> None:
        super().__init__(message)
        self.persist = persist


def load(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise QueueError(f"fila invalida (esperado lista): {path}")
    return data


def save(path: str | Path, items: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def find(items: list[dict[str, Any]], dedupe_key: str) -> dict[str, Any] | None:
    return next((i for i in items if i.get("dedupe_key") == dedupe_key), None)


def _expired(item: dict[str, Any], reference: datetime) -> bool:
    try:
        return stamp(item["expires_at"]) <= reference
    except (KeyError, ValueError, TypeError):
        return True


def next_ready(path: str | Path, reference: datetime | None = None) -> dict[str, Any] | None:
    """Melhor candidato publicavel: `ready`, nao vencido, maior total.

    Empate resolvido pelo dedupe_key, para que duas execucoes com o mesmo
    estado escolham sempre o mesmo item.
    """
    reference = reference or now()
    ready = [i for i in load(path)
             if i.get("status") in CLAIMABLE and not _expired(i, reference)]
    if not ready:
        return None
    return sorted(ready, key=lambda c: (-c.get("total", 0), c.get("dedupe_key", "")))[0]


def _transition(path: str | Path, dedupe_key: str, mutate) -> dict[str, Any]:
    items = load(path)
    item = find(items, dedupe_key)
    if item is None:
        raise QueueError(f"item ausente na fila: {dedupe_key}")
    try:
        mutate(item)
    except QueueError as exc:
        if exc.persist:
            save(path, items)
        raise
    save(path, items)
    return item


def claim(path: str | Path, dedupe_key: str,
          reference: datetime | None = None) -> dict[str, Any]:
    """Marca o item como `publishing` antes de qualquer chamada a Meta.

    Recusa item ja publicado, ja em publicacao, vencido ou vetado — a recusa e
    o ponto que impede republicacao em reexecucao de workflow.
    """
    reference = reference or now()

    def mutate(item: dict[str, Any]) -> None:
        status = item.get("status")
        if status in FINAL:
            raise QueueError(f"{dedupe_key}: ja publicado em {item.get('published_at')}")
        if status in NEEDS_REVIEW:
            raise QueueError(f"{dedupe_key}: estado 'unknown' exige conferencia humana")
        if status == "publishing":
            raise QueueError(f"{dedupe_key}: ja reivindicado em {item.get('claimed_at')}")
        if status not in CLAIMABLE:
            raise QueueError(f"{dedupe_key}: status {status!r} nao e publicavel")
        if _expired(item, reference):
            item["status"] = "expired"
            raise QueueError(f"{dedupe_key}: janela vencida em {item.get('expires_at')}",
                             persist=True)
        item["status"] = "publishing"
        item["claimed_at"] = iso(reference)
        item.pop("release_reason", None)

    return _transition(path, dedupe_key, mutate)


def commit(path: str | Path, dedupe_key: str, media_id: str,
           reference: datetime | None = None) -> dict[str, Any]:
    """Confirma a publicacao. `published_at` e o que `evaluate()` le como historico."""
    reference = reference or now()

    def mutate(item: dict[str, Any]) -> None:
        if item.get("status") not in {"publishing", "unknown"}:
            raise QueueError(f"{dedupe_key}: commit exige 'publishing', veio {item.get('status')!r}")
        item["status"] = "published"
        item["published_at"] = iso(reference)
        item["media_id"] = media_id
        item.pop("release_reason", None)

    return _transition(path, dedupe_key, mutate)


def release(path: str | Path, dedupe_key: str, reason: str) -> dict[str, Any]:
    """Devolve para `ready` — so quando e certo que NAO existe midia publicada."""
    def mutate(item: dict[str, Any]) -> None:
        if item.get("status") != "publishing":
            raise QueueError(f"{dedupe_key}: release exige 'publishing', veio {item.get('status')!r}")
        item["status"] = "ready"
        item["release_reason"] = reason
        item.pop("claimed_at", None)

    return _transition(path, dedupe_key, mutate)


def mark_unknown(path: str | Path, dedupe_key: str, reason: str) -> dict[str, Any]:
    """Falha depois que a Meta pode ter aceitado: nunca mais tenta sozinho."""
    def mutate(item: dict[str, Any]) -> None:
        item["status"] = "unknown"
        item["release_reason"] = reason

    return _transition(path, dedupe_key, mutate)


def history(path: str | Path) -> list[dict[str, Any]]:
    """Historico no formato que `engine.evaluate` consome, mais novo por ultimo."""
    published = [i for i in load(path)
                 if i.get("status") == "published" and i.get("published_at")]
    return sorted(published, key=lambda i: i["published_at"])

"""Camada comum dos coletores.

Plano Mestre secoes 12.3, 17.3 e 18: toda fonte tem timeout, retries limitados,
cache e politica de fallback; falha de fonte nunca vira dado zero silencioso.
Cada coleta devolve um SourceResult com fetched_at, status e fallback_used, que
o normalizador copia para o bloco `sources` do snapshot.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from .. import config

CACHE_DIR = config.ROOT / "output" / ".cache"
TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo, sem DST desde 2019


def now() -> datetime:
    return datetime.now(TZ)


def iso(moment: datetime | None = None) -> str:
    return (moment or now()).isoformat(timespec="seconds")


@dataclass
class SourceResult:
    """Resultado de uma coleta, com a procedencia que o snapshot precisa."""

    name: str
    status: str                       # ok | degraded | failed | not_collected | cached
    fetched_at: str = field(default_factory=iso)
    payload: Any = None
    model_run: str | None = None
    valid_for: str | None = None
    fallback_used: bool = False
    detail: str | None = None
    age_minutes: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "cached", "degraded"}

    @property
    def usable(self) -> bool:
        return self.status in {"ok", "cached"}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("payload", None)
        return data


def not_collected(name: str, reason: str = "fonte desligada em fontes.yaml") -> SourceResult:
    return SourceResult(name=name, status="not_collected", detail=reason)


def _cache_path(name: str, key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120]
    return CACHE_DIR / name / f"{safe}.json"


def read_cache(name: str, key: str, ttl_minutes: int) -> tuple[Any, float] | None:
    path = _cache_path(name, key)
    if not path.exists():
        return None
    age_minutes = (time.time() - path.stat().st_mtime) / 60
    if age_minutes > ttl_minutes:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")), age_minutes
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(name: str, key: str, payload: Any) -> None:
    path = _cache_path(name, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def get_json(
    source_name: str,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    cache_key: str | None = None,
    session: requests.Session | None = None,
) -> SourceResult:
    """GET com timeout, retries limitados e cache, guiado por fontes.yaml.

    Nunca levanta excecao de rede: devolve status 'failed' com o detalhe, para
    que o snapshot registre a falha em vez de publicar um buraco silencioso.
    """
    spec = config.source(source_name)
    if not spec.get("enabled", False):
        return not_collected(source_name)

    timeout = int(spec.get("timeout_seconds", 25))
    retries = int(spec.get("retries", 2))
    backoff = float(spec.get("backoff_seconds", 3))
    ttl = int(spec.get("cache_ttl_minutes", 30))
    key = cache_key or json.dumps(params or {}, sort_keys=True)

    cached = read_cache(source_name, key, ttl)
    if cached is not None:
        payload, age = cached
        return SourceResult(source_name, "cached", payload=payload, age_minutes=round(age, 1))

    http = session or requests
    last_error = ""
    for attempt in range(retries + 1):
        try:
            response = http.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            write_cache(source_name, key, payload)
            return SourceResult(source_name, "ok", payload=payload)
        except Exception as exc:  # rede, HTTP, JSON
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))

    stale = read_cache(source_name, key, ttl_minutes=10 ** 6)
    if stale is not None:
        payload, age = stale
        return SourceResult(source_name, "degraded", payload=payload,
                            age_minutes=round(age, 1), fallback_used=True,
                            detail=f"cache vencido apos falha: {last_error}")
    return SourceResult(source_name, "failed", detail=last_error)


def with_fallback(primary: SourceResult, fallback: Callable[[], SourceResult]) -> SourceResult:
    """Aplica a fonte de fallback declarada em fontes.yaml e marca fallback_used."""
    if primary.usable:
        return primary
    alternative = fallback()
    if alternative.ok:
        alternative.fallback_used = True
        alternative.detail = f"fallback de {primary.name}: {primary.detail or primary.status}"
        return alternative
    return primary


def is_fresh(result: SourceResult, source_name: str, reference: datetime | None = None) -> bool:
    """Frescor pelo freshness_ttl_minutes da fonte (gate de veto da secao 8.1)."""
    spec = config.source(source_name)
    ttl = spec.get("freshness_ttl_minutes")
    if ttl is None:
        return result.usable
    if not result.ok:
        return False
    fetched = datetime.fromisoformat(result.fetched_at)
    age = ((reference or now()) - fetched).total_seconds() / 60 + result.age_minutes
    return age <= float(ttl)

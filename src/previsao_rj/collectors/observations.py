"""Observacao: INMET e CEMADEN — Plano Mestre v1.1, secoes 5.1, 5.3 e 12.1.

Estado atual: DESLIGADO em `config/fontes.yaml`. Enquanto estiver assim, este
modulo devolve `not_collected` e o criterio "observacao compativel" do score de
confianca vale 0 — que e o comportamento honesto: nao ha observacao confirmando
nada, e o snapshot registra isso em vez de fingir 100 pontos.

Ligar exige, nesta ordem:
  1. validar o formato real de resposta de cada endpoint contra uma fixture;
  2. mapear as estacoes que cobrem cada zona de `locais_rj.yaml`;
  3. aplicar o QC do CEMADEN (secao 5.3): dado bruto so vira manchete depois de
     validacao de faixa e de timestamp em UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .. import config
from .base import SourceResult, get_json, not_collected, with_fallback

INMET = "inmet_estacoes"
CEMADEN = "cemaden_pluviometros"


def collect(locations: list[dict[str, Any]]) -> SourceResult:
    """Observacao consolidada, com o fallback declarado em fontes.yaml."""
    primary = fetch_inmet(locations)
    if config.source(INMET).get("fallback") == CEMADEN:
        return with_fallback(primary, lambda: fetch_cemaden(locations))
    return primary


def fetch_inmet(locations: list[dict[str, Any]]) -> SourceResult:
    spec = config.source(INMET)
    if not spec.get("enabled", False):
        return not_collected(INMET, "INMET desligado ate a validacao de formato")
    return get_json(INMET, spec["endpoint"], cache_key="estacoes")


def fetch_cemaden(locations: list[dict[str, Any]]) -> SourceResult:
    spec = config.source(CEMADEN)
    if not spec.get("enabled", False):
        return not_collected(CEMADEN, "CEMADEN desligado ate a validacao de QC")
    result = get_json(CEMADEN, spec["endpoint"], cache_key="pluviometros")
    if result.usable:
        result.payload = quality_control(result.payload, spec.get("quality_control") or {})
    return result


def quality_control(payload: Any, rules: dict[str, Any]) -> Any:
    """QC do dado bruto do CEMADEN (secao 5.3).

    Descarta leitura fora de faixa e leitura sem timestamp em UTC, marcando cada
    exclusao. Dado suspeito nao e apagado em silencio: vai para `rejected`.
    """
    max_hourly = float(rules.get("max_hourly_mm", 120))
    require_utc = bool(rules.get("require_timestamp_utc", True))
    readings = payload if isinstance(payload, list) else (payload or {}).get("readings") or []

    accepted, rejected = [], []
    for item in readings:
        value = item.get("valor") if isinstance(item, dict) else None
        stamp = item.get("datahora") if isinstance(item, dict) else None
        try:
            millimeters = float(value)
        except (TypeError, ValueError):
            rejected.append({"item": item, "reason": "valor nao numerico"})
            continue
        if millimeters < 0 or millimeters > max_hourly:
            rejected.append({"item": item, "reason": f"fora da faixa 0..{max_hourly} mm"})
            continue
        if require_utc and not _has_utc_timestamp(stamp):
            rejected.append({"item": item, "reason": "timestamp sem UTC explicito"})
            continue
        accepted.append(item)

    return {"readings": accepted, "rejected": rejected,
            "quality_control": {"max_hourly_mm": max_hourly, "require_timestamp_utc": require_utc}}


def _has_utc_timestamp(stamp: Any) -> bool:
    if not isinstance(stamp, str):
        return False
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(None)

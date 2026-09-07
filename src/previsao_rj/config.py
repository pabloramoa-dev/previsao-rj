"""Carregamento e validacao das configuracoes versionadas.

Plano Mestre secao 12.3: nada de hardcode. Locais, fontes, limiares, horarios
e marca vivem em YAML validado e sao lidos por aqui.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

SAMPLE_TIERS = {1, 2, 3}
SPATIAL_FITS = {"alto", "medio", "baixo"}


def _read_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"configuracao ausente: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"configuracao invalida (esperado mapa): {path}")
    return data


@lru_cache(maxsize=None)
def load_places() -> dict[str, Any]:
    """config/locais_rj.yaml, ja validado."""
    data = _read_yaml("locais_rj.yaml")
    validate_places(data)
    return data


@lru_cache(maxsize=None)
def load_sources() -> dict[str, Any]:
    """config/fontes.yaml com os defaults ja aplicados em cada fonte."""
    data = _read_yaml("fontes.yaml")
    defaults = data.get("defaults", {})
    merged: dict[str, Any] = {}
    for name, spec in (data.get("sources") or {}).items():
        item = dict(defaults)
        item.update(spec or {})
        item["name"] = name
        merged[name] = item
    data["sources"] = merged
    return data


@lru_cache(maxsize=None)
def load_thresholds() -> dict[str, Any]:
    return _read_yaml("thresholds.yml").get("thresholds", {})


@lru_cache(maxsize=None)
def load_brand() -> dict[str, Any]:
    return _read_yaml("brand.yml").get("brand", {})


@lru_cache(maxsize=None)
def load_schedule() -> dict[str, Any]:
    return _read_yaml("schedule.yml")


def validate_places(data: dict[str, Any]) -> None:
    """Falha cedo em erro de cadastro: id duplicado, zona inexistente,
    coordenada fora do recorte metropolitano ou alias repetido entre locais."""
    zones = data.get("zones") or {}
    municipalities = data.get("municipalities") or {}
    locations = data.get("locations") or []
    if not locations:
        raise ValueError("locais_rj.yaml sem locais")

    seen_ids: set[str] = set()
    alias_owner: dict[str, str] = {}
    ambiguous = {a.casefold() for a in (data.get("ambiguous") or {})}

    for loc in locations:
        loc_id = loc.get("id")
        if not loc_id:
            raise ValueError(f"local sem id: {loc}")
        if loc_id in seen_ids:
            raise ValueError(f"id duplicado em locais_rj.yaml: {loc_id}")
        seen_ids.add(loc_id)

        if loc.get("zone") not in zones:
            raise ValueError(f"{loc_id}: zona desconhecida {loc.get('zone')!r}")
        if loc.get("municipality") not in municipalities:
            raise ValueError(f"{loc_id}: municipio desconhecido {loc.get('municipality')!r}")
        if loc.get("sample_tier") not in SAMPLE_TIERS:
            raise ValueError(f"{loc_id}: sample_tier invalido {loc.get('sample_tier')!r}")
        if loc.get("spatial_fit") not in SPATIAL_FITS:
            raise ValueError(f"{loc_id}: spatial_fit invalido {loc.get('spatial_fit')!r}")

        lat, lon = loc.get("latitude"), loc.get("longitude")
        if not (-23.15 <= float(lat) <= -22.60):
            raise ValueError(f"{loc_id}: latitude fora do recorte metropolitano ({lat})")
        if not (-43.80 <= float(lon) <= -42.95):
            raise ValueError(f"{loc_id}: longitude fora do recorte metropolitano ({lon})")

        for alias in loc.get("aliases") or []:
            key = alias.casefold().strip()
            if key in ambiguous:
                continue  # alias ambiguo pode pertencer a mais de um local
            if key in alias_owner and alias_owner[key] != loc_id:
                raise ValueError(
                    f"alias {alias!r} repetido entre {alias_owner[key]} e {loc_id}; "
                    "declare em 'ambiguous' se for mesmo ambiguo"
                )
            alias_owner[key] = loc_id

    for alias, candidates in (data.get("ambiguous") or {}).items():
        poi_ids = {p["id"] for group in (data.get("points_of_interest") or {}).values()
                   for p in group}
        for cand in candidates:
            if cand not in seen_ids and cand not in poi_ids:
                raise ValueError(f"ambiguous[{alias!r}] aponta para id inexistente: {cand}")


def locations_by_tier(max_tier: int = 1) -> list[dict[str, Any]]:
    """Locais que entram na amostra ate o tier pedido, em ordem estavel."""
    places = load_places()
    picked = [l for l in places["locations"] if int(l["sample_tier"]) <= max_tier]
    return sorted(picked, key=lambda l: (l["sample_tier"], l["id"]))


def location_by_id(loc_id: str) -> dict[str, Any] | None:
    for loc in load_places()["locations"]:
        if loc["id"] == loc_id:
            return loc
    return None


def source(name: str) -> dict[str, Any]:
    sources = load_sources()["sources"]
    if name not in sources:
        raise KeyError(f"fonte nao cadastrada em fontes.yaml: {name}")
    return sources[name]


def forbidden_weather_sources() -> set[str]:
    return set(load_sources().get("forbidden_weather_sources") or [])

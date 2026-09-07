"""Resolver geografico — Plano Mestre v1.1, secao 4.4.

Entende acento, abreviacao e ambiguidade. "Icarai" aponta Niteroi; "Caxias"
aponta Duque de Caxias mas pede confirmacao; "Centro" e "Barra" perguntam o
municipio antes de responder.

Este modulo e a base do atendimento por comentario e DM (Fase 6). Nao publica
nada e nao guarda conversa: recebe texto, devolve local ou pergunta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Any

from .. import config

_NOISE = re.compile(r"[^a-z0-9 ]+")
_STOPWORDS = {
    "bom", "boa", "dia", "tarde", "noite", "por", "favor", "obrigado", "obrigada",
    "e", "o", "a", "de", "do", "da", "em", "no", "na", "pra", "para", "aqui",
    "como", "vai", "estar", "ta", "hoje", "amanha", "tempo", "previsao", "chuva",
    "sol", "calor", "frio", "vento", "praia", "oi", "ola", "quero", "saber",
}


def normalize(text: str) -> str:
    """minusculas, sem acento, sem pontuacao, espacos colapsados."""
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = _NOISE.sub(" ", folded.casefold())
    return " ".join(folded.split())


@dataclass
class Resolution:
    status: str                                  # resolved | ambiguous | unknown
    location: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    matched_alias: str | None = None
    question: str | None = None
    confidence: str = "exata"                    # exata | aproximada

    @property
    def resolved(self) -> bool:
        return self.status == "resolved"


class GeoResolver:
    def __init__(self, places: dict[str, Any] | None = None) -> None:
        self.places = places or config.load_places()
        self.locations = {l["id"]: l for l in self.places["locations"]}
        self.pois = {p["id"]: p
                     for group in (self.places.get("points_of_interest") or {}).values()
                     for p in group}
        self.ambiguous = {normalize(k): v
                          for k, v in (self.places.get("ambiguous") or {}).items()}
        self.index = self._build_index()

    def _build_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}

        def add(key: str, target_id: str) -> None:
            key = normalize(key)
            if not key:
                return
            index.setdefault(key, [])
            if target_id not in index[key]:
                index[key].append(target_id)

        for loc in self.places["locations"]:
            add(loc["name"], loc["id"])
            add(loc["id"].replace("_", " "), loc["id"])
            for alias in loc.get("aliases") or []:
                add(alias, loc["id"])
        for group, items in (self.places.get("points_of_interest") or {}).items():
            for poi in items:
                # Praia nao e um lugar separado do bairro: "Icarai" e "Barra da
                # Tijuca" tem que cair no bairro, nao virar ambiguidade artificial.
                target_id = poi.get("location", poi["id"]) if group == "beaches" else poi["id"]
                add(poi["name"], target_id)
                for alias in poi.get("aliases") or []:
                    add(alias, target_id)
        return index

    # ------------------------------------------------------------------
    def target(self, target_id: str) -> dict[str, Any] | None:
        return self.locations.get(target_id) or self.pois.get(target_id)

    def _municipality_name(self, target: dict[str, Any]) -> str:
        key = target.get("municipality")
        return ((self.places.get("municipalities") or {}).get(key) or {}).get("name", key or "")

    def _ambiguity_question(self, key: str, candidates: list[dict[str, Any]]) -> str:
        if len(candidates) > 1:
            options = " ou ".join(
                f"{c['name']} ({self._municipality_name(c)})" for c in candidates)
            return f"Voce quis dizer {options}?"
        single = candidates[0]
        return (f"Voce quis dizer {single['name']}, "
                f"em {self._municipality_name(single)}?")

    def resolve(self, text: str, *, municipality_hint: str | None = None) -> Resolution:
        """Resolve o texto de um comentario ou DM em um local do cadastro."""
        key = normalize(text)
        if not key:
            return Resolution("unknown")

        # 1. casamento direto do texto inteiro
        hit = self._lookup(key, municipality_hint)
        if hit is not None:
            return hit

        # 2. remove ruido conversacional e tenta de novo
        cleaned = " ".join(w for w in key.split() if w not in _STOPWORDS)
        if cleaned and cleaned != key:
            hit = self._lookup(cleaned, municipality_hint)
            if hit is not None:
                return hit

        # 3. maior n-grama presente no cadastro (pega "vou pra tijuca amanha")
        words = cleaned.split() or key.split()
        for size in range(min(4, len(words)), 0, -1):
            for start in range(len(words) - size + 1):
                hit = self._lookup(" ".join(words[start:start + size]), municipality_hint)
                if hit is not None:
                    return hit

        # 4. erro de digitacao
        approx = get_close_matches(cleaned or key, list(self.index), n=1, cutoff=0.86)
        if approx:
            hit = self._lookup(approx[0], municipality_hint)
            if hit is not None:
                hit.confidence = "aproximada"
                return hit

        return Resolution("unknown")

    def _lookup(self, key: str, municipality_hint: str | None) -> Resolution | None:
        if key in self.ambiguous:
            candidates = [t for t in (self.target(c) for c in self.ambiguous[key]) if t]
            if municipality_hint:
                narrowed = [c for c in candidates if c.get("municipality") == municipality_hint]
                if len(narrowed) == 1:
                    return Resolution("resolved", location=narrowed[0], matched_alias=key)
            return Resolution("ambiguous", candidates=candidates, matched_alias=key,
                              question=self._ambiguity_question(key, candidates))

        target_ids = self.index.get(key)
        if not target_ids:
            return None
        targets = [t for t in (self.target(i) for i in target_ids) if t]
        if municipality_hint:
            narrowed = [t for t in targets if t.get("municipality") == municipality_hint]
            if narrowed:
                targets = narrowed
        if len(targets) == 1:
            return Resolution("resolved", location=targets[0], matched_alias=key)
        return Resolution("ambiguous", candidates=targets, matched_alias=key,
                          question=self._ambiguity_question(key, targets))


_default: GeoResolver | None = None


def resolve(text: str, *, municipality_hint: str | None = None) -> Resolution:
    global _default
    if _default is None:
        _default = GeoResolver()
    return _default.resolve(text, municipality_hint=municipality_hint)

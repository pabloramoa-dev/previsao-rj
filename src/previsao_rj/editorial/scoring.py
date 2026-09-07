"""Compatibilidade do score público com a seleção editorial explicável."""
from .engine import candidates, classify


def score_snapshot(snapshot: dict) -> dict:
    options = candidates(snapshot)
    if not options:
        return {"total": 0, "classification": "skip", "parts": {}}
    best = max(options, key=lambda c: sum(c["parts"].values()))
    parts = dict(best["parts"], novelty=5)
    total = sum(parts.values())
    return {"total": total, "classification": classify(total), "parts": parts}

from __future__ import annotations


def score_snapshot(snapshot: dict) -> dict:
    locs = snapshot["forecast"]["today"]["locations"]
    max_t = max(x["max_c"] for x in locs)
    min_max_t = min(x["max_c"] for x in locs)
    max_rain = max(x.get("rain_probability_pct", 0) for x in locs)
    utility = 5 if max_rain >= 45 or max_t >= 34 else 3
    urgency = 4 if max_rain >= 55 else 3
    contrast = 5 if max_t - min_max_t >= 4 else 2
    shareability = 4
    novelty = 3
    total = utility + urgency + contrast + shareability + novelty
    kind = "reel_priority" if total >= 19 else "reel" if total >= 14 else "story" if total >= 9 else "skip"
    return {"total": total, "classification": kind, "parts": {
        "utility": utility, "urgency": urgency, "contrast": contrast,
        "shareability": shareability, "novelty": novelty}}

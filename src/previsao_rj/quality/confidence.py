"""Score de confianca do dado — Plano Mestre v1.1, secao 5.2.

Criterio                  Peso   O que mede
------------------------  -----  ------------------------------------------------
Concordancia de modelos    0-30  ECMWF e secundarios apontam a mesma coisa
Atualidade da rodada       0-20  quao recente e o dado que estamos usando
Consistencia temporal      0-15  rodadas sucessivas mantem o sinal
Observacao compativel      0-20  INMET/CEMADEN confirmam a evolucao
Adequacao espacial         0-15  o ponto representa mesmo a zona

Cortes operacionais:
  < 50  -> proibido usar linguagem categorica
  < 35  -> bloquear Reel de alerta; preferir Story de incerteza ou nao publicar

Enquanto observacao (INMET/CEMADEN) estiver desligada em fontes.yaml, o criterio
correspondente vale 0 e isso fica REGISTRADO em `notes`. O teto passa a ser 80 —
e correto que seja: nao ha observacao confirmando nada.
"""
from __future__ import annotations

from datetime import datetime
from statistics import pstdev
from typing import Any

WEIGHTS = {
    "model_agreement": 30,
    "run_recency": 20,
    "temporal_consistency": 15,
    "observation_match": 20,
    "spatial_fit": 15,
}

MIN_FOR_CATEGORICAL = 50   # abaixo disso, linguagem probabilistica obrigatoria
MIN_FOR_ALERT = 35         # abaixo disso, Reel de alerta bloqueado

SPATIAL_FIT_SCORE = {"alto": 15, "medio": 10, "baixo": 5}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def model_agreement(per_model: dict[str, dict[str, Any]]) -> tuple[float, str]:
    """Dispersao entre modelos para maxima e probabilidade de chuva.

    Referencia de tolerancia: 1,5 C de desvio-padrao na maxima e 12 pontos
    percentuais na chuva ja consomem metade do peso.
    """
    usable = {m: v for m, v in per_model.items() if v}
    if len(usable) < 2:
        return 12.0, "so um modelo disponivel: concordancia nao verificavel"

    maxima = [v["max_c"] for v in usable.values() if v.get("max_c") is not None]
    rain = [v["rain_probability_pct"] for v in usable.values()
            if v.get("rain_probability_pct") is not None]

    temp_sd = pstdev(maxima) if len(maxima) > 1 else 0.0
    rain_sd = pstdev(rain) if len(rain) > 1 else 0.0

    temp_part = 15 * _clamp(1 - temp_sd / 3.0, 0, 1)     # 3 C de desvio zera
    rain_part = 15 * _clamp(1 - rain_sd / 25.0, 0, 1)    # 25 p.p. de desvio zera
    score = round(temp_part + rain_part, 1)
    return score, (f"{len(usable)} modelos; desvio maxima {temp_sd:.1f} C, "
                   f"desvio chuva {rain_sd:.0f} p.p.")


def run_recency(age_minutes: float, ttl_minutes: float = 120) -> tuple[float, str]:
    """Decai linearmente ate o TTL de frescor da fonte."""
    if age_minutes < 0:
        age_minutes = 0.0
    score = round(WEIGHTS["run_recency"] * _clamp(1 - age_minutes / max(ttl_minutes, 1), 0, 1), 1)
    return score, f"dado com {age_minutes:.0f} min (TTL {ttl_minutes:.0f} min)"


def temporal_consistency(previous: dict[str, Any] | None,
                         current: dict[str, Any]) -> tuple[float, str]:
    """Compara com o snapshot anterior: o sinal se manteve entre rodadas?

    Sem snapshot anterior nao ha o que comparar; damos metade do peso e
    registramos, em vez de premiar ou punir sem evidencia.
    """
    if not previous:
        return 7.5, "sem snapshot anterior para comparar"
    try:
        prev_rain = float(previous["rain_probability_pct"])
        prev_max = float(previous["max_c"])
        rain_delta = abs(float(current["rain_probability_pct"]) - prev_rain)
        temp_delta = abs(float(current["max_c"]) - prev_max)
    except (KeyError, TypeError, ValueError):
        return 7.5, "snapshot anterior incompleto"
    rain_part = 8 * _clamp(1 - rain_delta / 30.0, 0, 1)
    temp_part = 7 * _clamp(1 - temp_delta / 4.0, 0, 1)
    score = round(rain_part + temp_part, 1)
    return score, f"variacao entre rodadas: chuva {rain_delta:.0f} p.p., maxima {temp_delta:.1f} C"


def observation_match(observed_status: str,
                      agreement: float | None = None) -> tuple[float, str]:
    """INMET/CEMADEN confirmando a evolucao. `agreement` em 0..1 quando houver."""
    if observed_status in {"not_collected", "failed"}:
        return 0.0, "sem observacao (INMET/CEMADEN desligados ou indisponiveis)"
    if agreement is None:
        return 10.0, "observacao presente, comparacao ainda nao implementada"
    return round(WEIGHTS["observation_match"] * _clamp(agreement, 0, 1), 1), \
        f"observacao concorda em {agreement * 100:.0f}%"


def spatial_fit(fits: list[str]) -> tuple[float, str]:
    """Media do quanto os pontos usados representam suas zonas."""
    if not fits:
        return 0.0, "nenhum local avaliado"
    scores = [SPATIAL_FIT_SCORE.get(f, 5) for f in fits]
    score = round(sum(scores) / len(scores), 1)
    baixos = sum(1 for f in fits if f == "baixo")
    detail = f"{len(fits)} pontos avaliados"
    if baixos:
        detail += f"; {baixos} de microclima marcado"
    return score, detail


def level(score: float) -> str:
    if score >= 75:
        return "alta"
    if score >= MIN_FOR_CATEGORICAL:
        return "media"
    if score >= MIN_FOR_ALERT:
        return "baixa"
    return "insuficiente"


def compute(
    *,
    per_model: dict[str, dict[str, Any]],
    age_minutes: float,
    freshness_ttl_minutes: float,
    previous_reference: dict[str, Any] | None,
    current_reference: dict[str, Any],
    observed_status: str,
    observation_agreement: float | None,
    spatial_fits: list[str],
) -> dict[str, Any]:
    """Devolve o score consolidado, as partes e os gates ja resolvidos."""
    parts: dict[str, float] = {}
    notes: list[str] = []

    for key, (value, note) in {
        "model_agreement": model_agreement(per_model),
        "run_recency": run_recency(age_minutes, freshness_ttl_minutes),
        "temporal_consistency": temporal_consistency(previous_reference, current_reference),
        "observation_match": observation_match(observed_status, observation_agreement),
        "spatial_fit": spatial_fit(spatial_fits),
    }.items():
        parts[key] = value
        notes.append(f"{key}: {note}")

    total = round(sum(parts.values()), 1)
    return {
        "score": total,
        "max_possible": sum(WEIGHTS.values()),
        "level": level(total),
        "parts": parts,
        "weights": dict(WEIGHTS),
        "notes": notes,
        "gates": {
            "allow_categorical_language": total >= MIN_FOR_CATEGORICAL,
            "allow_alert_reel": total >= MIN_FOR_ALERT,
        },
        "computed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

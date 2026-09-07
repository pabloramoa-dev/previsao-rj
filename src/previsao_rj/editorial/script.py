"""Roteiros ancorados nos valores disponíveis, sem contraste inventado."""
from __future__ import annotations
import math
from .contrast import regional_contrast


def number(value):
    return isinstance(value, (float, int)) and math.isfinite(value)


def build_script(snapshot: dict) -> dict:
    locs = snapshot["forecast"]["today"]["locations"]
    temps = [e for e in locs if number(e.get("max_c"))]
    rains = [e for e in locs if number(e.get("rain_probability_pct"))]
    if not temps:
        raise ValueError("Sem temperatura válida para o roteiro")
    hottest = max(temps, key=lambda x: x["max_c"])
    coolest = min(temps, key=lambda x: x["max_c"])
    wettest = max(rains, key=lambda x: x["rain_probability_pct"]) if rains else None
    contrast = regional_contrast(locs)
    if contrast["temperature"]["relevant"]:
        hook = "A TEMPERATURA MUDA PELA REGIÃO"
        text = (f"No Rio, {hottest['name']} tem máxima prevista de {hottest['max_c']:g} graus. "
                f"Em {coolest['name']}, são {coolest['max_c']:g} graus. ")
    else:
        hook = "RIO ANTES DE SAIR"
        text = (f"No Rio, as máximas previstas ficam entre {coolest['max_c']:g} "
                f"e {hottest['max_c']:g} graus nos pontos consultados. ")
    if contrast["gust"]["relevant"]:
        high = contrast["gust"]["high"]
        text += f"Atenção ao vento: rajadas previstas de até {high['value']:g} quilômetros por hora em {high['name']}. "
    if wettest:
        text += (f"Em {wettest['name']}, a probabilidade de chuva no dia é de "
                 f"{wettest['rain_probability_pct']:g} por cento. Isso não significa chuva o dia inteiro. ")
    else:
        text += "A probabilidade de chuva não está disponível nesta coleta. "
    text += "Confira a atualização antes de sair. Previsão RJ. O tempo do Rio para decidir seu dia."
    return {"hook": hook, "narration": text, "hottest": hottest, "coolest": coolest, "wettest": wettest}

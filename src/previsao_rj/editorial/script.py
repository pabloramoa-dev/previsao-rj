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


# Janela larga nao informa nada. Em 15/09/2026 o Reel e a legenda anunciaram
# "maior chance entre 00:00 e 23:00": tecnicamente verdadeiro, editorialmente
# inutil — o dia inteiro anunciado como se fosse um recorte. Quando a janela
# passa de LARGA_H horas, o que informa e o PICO, que o snapshot ja calcula.
LARGA_H = 8


def _hora(texto):
    try:
        return int(str(texto).split(':')[0])
    except (ValueError, AttributeError, IndexError):
        return None


def janela_legivel(janela: dict | None) -> dict | None:
    """Traduz `rain_window` no que vale dizer: faixa estreita ou hora do pico.

    Devolve `None` quando nao ha nada confiavel a dizer — e ai a linha nao entra,
    em vez de anunciar o dia inteiro como se fosse um horario.
    """
    if not isinstance(janela, dict):
        return None
    inicio, fim = janela.get('start'), janela.get('end')
    h_inicio, h_fim = _hora(inicio), _hora(fim)
    if h_inicio is None or h_fim is None or h_fim <= h_inicio:
        return None
    if h_fim - h_inicio < LARGA_H:
        return {'tipo': 'faixa', 'inicio': inicio, 'fim': fim}
    pico = janela.get('peak_hour')
    prob = janela.get('peak_probability_pct')
    if pico and number(prob):
        return {'tipo': 'pico', 'hora': pico, 'probabilidade': prob}
    return None

"""Painel informativo do Previsão RJ, inspirado nos cards do Sul Fluminense.

Não importa arquivos do outro repositório. Valores ausentes nunca viram zero.
Desenhado na metade direita do Reel para preservar o apresentador.
"""
from __future__ import annotations
import math
from PIL import ImageDraw, ImageFont

INK = "#12314B"
BLUE = "#2374AE"
WHITE = "#FFFFFF"
FONT_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"


def valid(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def value_of(loc, key, unit="", decimals=0):
    v = loc.get(key)
    if not valid(v):
        return "—"
    return f"{v:.{decimals}f}".replace(".", ",") + unit


def metrics(loc):
    return [
        ("Máxima", value_of(loc, "max_c", "°C")),
        ("Mínima", value_of(loc, "min_c", "°C")),
        ("Chance de chuva", value_of(loc, "rain_probability_pct", "%")),
        ("Volume previsto", value_of(loc, "rain_mm", " mm", 1)),
        ("Rajadas", value_of(loc, "gust_kmh", " km/h")),
    ]


def _font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def _fit(draw, label, font, max_width):
    if draw.textbbox((0, 0), label, font=font)[2] <= max_width:
        return label
    while label and draw.textbbox((0, 0), label + "…", font=font)[2] > max_width:
        label = label[:-1]
    return label + "…"


def draw_weather_panel(draw: ImageDraw.ImageDraw, loc: dict, x=219, y=365, w=304):
    """Retorna o retângulo usado pelo painel; coordenadas em canvas 540x960."""
    h = 405
    draw.rounded_rectangle((x, y, x+w, y+h), radius=22, fill=WHITE, outline="#B5D7EA", width=3)
    draw.rounded_rectangle((x+10, y+10, x+w-10, y+72), radius=14, fill=INK)
    title = _fit(draw, str(loc.get("name") or "Localidade"), _font(23, True), w-43)
    draw.text((x+21, y+21), title, font=_font(23, True), fill=WHITE)
    draw.text((x+21, y+79), "PREVISÃO DO DIA", font=_font(13, True), fill=BLUE)
    for i, (label, val) in enumerate(metrics(loc)):
        yy = y + 106 + i * 55
        if i:
            draw.line((x+19, yy-7, x+w-19, yy-7), fill="#E0EDF5", width=2)
        draw.text((x+20, yy), label, font=_font(16), fill="#476174")
        vf = _font(22 if len(val) < 9 else 18, True)
        width = draw.textbbox((0, 0), val, font=vf)[2]
        draw.text((x+w-20-width, yy+19), val, font=vf, fill=INK)
    draw.text((x+20, y+h-25), "Valores previstos · sujeito a atualização", font=_font(11), fill="#597287")
    return (x, y, x+w, y+h)

"""Checks for detailed weather panel, including missing-value safety."""
from src.previsao_rj.render.weather_panel import metrics, value_of, valid


def test_missing_numbers_are_not_zero():
    data = {"name": "Centro", "max_c": 30, "rain_probability_pct": None}
    result = dict(metrics(data))
    assert result["Máxima"] == "30°C"
    assert result["Mínima"] == "—"
    assert result["Chance de chuva"] == "—"
    assert result["Volume previsto"] == "—"
    assert result["Rajadas"] == "—"


def test_metrics_format_and_finiteness():
    data = {"max_c": 29, "min_c": 21, "rain_probability_pct": 65,
            "rain_mm": 2.25, "gust_kmh": 33}
    assert dict(metrics(data)) == {
        "Máxima": "29°C", "Mínima": "21°C", "Chance de chuva": "65%",
        "Volume previsto": "2,2 mm", "Rajadas": "33 km/h"}
    assert value_of({"max_c": float("nan")}, "max_c") == "—"
    assert not valid(True)


def test_panel_draws_on_portrait_canvas():
    from PIL import Image, ImageDraw
    from src.previsao_rj.render.weather_panel import draw_weather_panel
    image = Image.new("RGB", (540, 960), "white")
    bbox = draw_weather_panel(ImageDraw.Draw(image), {
        "name": "Nova Iguaçu", "max_c": 34, "min_c": 22,
        "rain_probability_pct": 70, "rain_mm": 3.2, "gust_kmh": 28})
    assert bbox == (219, 365, 523, 770)
    assert image.getpixel((240, 400)) != (255, 255, 255)

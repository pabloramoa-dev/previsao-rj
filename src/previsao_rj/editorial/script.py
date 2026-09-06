from __future__ import annotations


def build_script(snapshot: dict) -> dict:
    locs = snapshot["forecast"]["today"]["locations"]
    hottest = max(locs, key=lambda x: x["max_c"])
    coolest = min(locs, key=lambda x: x["max_c"])
    wettest = max(locs, key=lambda x: x.get("rain_probability_pct", 0))
    narration = (
        f"Hoje o Rio vai ter dois ritmos. {hottest['name']} chega perto de {hottest['max_c']} graus, "
        f"enquanto {coolest['name']} fica perto de {coolest['max_c']}. "
        f"A maior chance de chuva desta amostra aparece em {wettest['name']}, com {wettest.get('rain_probability_pct',0)} por cento. "
        "Se você sai no fim da tarde, confira a atualização antes de sair. "
        "Previsão RJ. O tempo do Rio para decidir seu dia."
    )
    return {"hook": "HOJE VÃO EXISTIR DOIS RIOS", "narration": narration,
            "hottest": hottest, "coolest": coolest, "wettest": wettest}

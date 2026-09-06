from __future__ import annotations

def build_caption(snapshot: dict) -> str:
    locs=snapshot['forecast']['today']['locations']
    hot=max(locs,key=lambda x:x['max_c'])
    cool=min(locs,key=lambda x:x['max_c'])
    wet=max(locs,key=lambda x:x.get('rain_probability_pct',0))
    return (f"Hoje o Rio pode ter contrastes importantes entre as regiões.\n\n"
            f"🌡️ {hot['name']}: até {hot['max_c']}°\n"
            f"🌤️ {cool['name']}: até {cool['max_c']}°\n"
            f"☔ {wet['name']}: maior chance de chuva da amostra, {wet.get('rain_probability_pct',0)}%\n\n"
            "Confira a atualização antes de sair.\n\n"
            "@previsaorj — O tempo do Rio para decidir seu dia.\n\n"
            "#PrevisaoRJ #RioDeJaneiro #TempoRJ")

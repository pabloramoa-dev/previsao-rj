"""Resumo comum à coleta: dados ausentes são exibidos, nunca tratados como zero."""
import json
import sys
from src.previsao_rj.editorial.contrast import regional_contrast


def summary(d):
    contrast=regional_contrast(d['forecast']['today']['locations'])
    print(f"## {d['forecast']['today']['date']} — Previsão RJ\n")
    print(f"Confiança: {d['confidence']['score']}/100\n")
    for key,label,unit in [('temperature','Temperatura','°C'),('rain','Chuva','p.p.'),('gust','Rajadas','km/h')]:
        c=contrast[key]
        print(f"- {label}: amplitude {c['spread']} {unit}; contraste relevante: {c['relevant']}")
    print('\n| Local | Máxima | Chuva | Rajadas | UV | Origem UV |\n|---|---|---|---|---|---|')
    for e in d['forecast']['today']['locations']:
        print(f"| {e['name']} | {e.get('max_c')} | {e.get('rain_probability_pct')} | {e.get('wind_gust_max_kmh')} | {e.get('uv_index_max')} | {e.get('field_provenance',{}).get('uv_index_max',{}).get('model')} |")


if __name__=='__main__':summary(json.load(open(sys.argv[1])))

"""Índices úteis inspirados no Sulflu, com dados e nomes próprios do RJ."""
import math

def number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def tips(locations):
    rain=[l['rain_probability_pct'] for l in locations if number(l.get('rain_probability_pct'))]
    uv=[l['uv_index_max'] for l in locations if number(l.get('uv_index_max'))]
    maximum=[l['max_c'] for l in locations if number(l.get('max_c'))]
    result=[]
    if rain and max(rain)>=60:result.append('LEVE GUARDA-CHUVA')
    elif rain and max(rain)>=30:result.append('PODE CHOVER: CONFIRA SUA REGIÃO')
    if uv and max(uv)>=6:result.append('UV ALTO: PROTETOR E SOMBRA')
    if maximum and max(maximum)<22:result.append('LEVE UM CASACO')
    if maximum and max(maximum)>=32:result.append('CALOR: LEVE ÁGUA')
    return result[:2]

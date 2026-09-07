"""Ondas modeladas por ponto, com data e grade; não avalia segurança de banho."""
from .base import get_json, not_collected, SourceResult
from .. import config

SOURCE='open_meteo_marine'


def collect(locations):
    beaches=[l for l in locations if l.get('beach')]
    if not beaches: return not_collected(SOURCE,'Nenhum ponto de praia na amostra')
    result=get_json(SOURCE,config.source(SOURCE)['endpoint'],{
        'latitude':','.join(str(l['latitude']) for l in beaches),
        'longitude':','.join(str(l['longitude']) for l in beaches),
        'timezone':'America/Sao_Paulo','forecast_days':7,
        'daily':'wave_height_max,wave_period_max'},cache_key='daily7|'+','.join(l['id'] for l in beaches))
    if not result.usable: return result
    raw=result.payload if isinstance(result.payload,list) else [result.payload]
    if len(raw)!=len(beaches): return SourceResult(SOURCE,'failed',detail='Quantidade de pontos incompatível')
    points={}
    for loc,item in zip(beaches,raw):
        daily=item.get('daily',{});dates=daily.get('time',[])
        if not dates: continue
        points[loc['id']]={'date':dates[0],'wave_height_max':(daily.get('wave_height_max') or [None])[0],
            'wave_period_max':(daily.get('wave_period_max') or [None])[0], 'daily':daily,
            'grid_latitude':item.get('latitude'),'grid_longitude':item.get('longitude')}
    if not points: return SourceResult(SOURCE,'failed',detail='Resposta sem datas marítimas')
    result.payload={'points':points,'interpretation':'previsao_modelada_na_grade; nao determina seguranca para banho'}
    return result

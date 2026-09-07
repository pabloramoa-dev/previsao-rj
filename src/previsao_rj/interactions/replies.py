"""Resposta geográfica fundamentada na coleta, sem envio automático."""
from ..geo.resolver import resolve
from ..normalizers.snapshot import is_stale


def prepare_reply(text, snapshot, municipality_hint=None, reference=None):
    resolution = resolve(text, municipality_hint=municipality_hint)
    if resolution.status == 'ambiguous':
        return {'status':'clarification','text':resolution.question}
    if not resolution.resolved:
        return {'status':'clarification','text':'Qual bairro e município você quer consultar?'}
    if resolution.confidence == 'aproximada':
        return {'status':'clarification','text':f"Você quis dizer {resolution.location['name']}?"}
    try:
        stale = is_stale(snapshot, reference=reference)
    except (KeyError, ValueError, TypeError): stale = True
    if stale:
        return {'status':'unavailable','text':'A coleta disponível precisa ser atualizada. Consulte novamente mais tarde.'}
    from ..geo.resolver import normalize
    key = 'tomorrow' if 'amanha' in normalize(text).split() else 'today'
    loc = next((e for e in snapshot['forecast'].get(key,{}).get('locations',[]) if e['id']==resolution.location.get('id')),None)
    if not loc:
        return {'status':'unavailable','text':f"Ainda não há uma coleta específica para {resolution.location['name']} nesta atualização."}
    parts = [f"{'Amanhã' if key=='tomorrow' else 'Hoje'} em {loc['name']}:"]
    if loc.get('min_c') is not None and loc.get('max_c') is not None:
        parts.append(f"mínima de {loc['min_c']}°C e máxima de {loc['max_c']}°C.")
    if loc.get('rain_probability_pct') is not None:
        parts.append(f"Probabilidade de chuva no dia: {loc['rain_probability_pct']}%; não significa chuva contínua.")
    parts.append('Atualização: '+snapshot['generated_at']+'. Previsão sujeita a mudanças.')
    return {'status':'draft','location_id':loc['id'],'text':' '.join(parts),'publication':False}

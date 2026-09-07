"""Cinco formatos com validação de dados antes de produzir a fala."""
from datetime import timedelta
from .engine import evaluate, stamp
from .script import build_script, number

TITLES = {'rio_antes_de_sair': 'RIO ANTES DE SAIR', 'chove_onde': 'O TEMPO MUDA ONDE?',
          'vai_dar_praia': 'VAI DAR PRAIA?', 'fim_de_semana': 'SEU FIM DE SEMANA', 'vai_ao_jogo': 'VAI AO JOGO?'}


def prepare(snapshot, format='rio_antes_de_sair', reference=None, history=None):
    options = [c for c in evaluate(snapshot, history, reference) if c['format'] == format and c['status'] == 'ready']
    if not options:
        raise ValueError(f'Formato {format} sem candidato válido e atualizado')
    candidate = options[0]
    locs = [e for e in snapshot['forecast']['today']['locations'] if e['id'] in candidate['location_ids']]
    lines = []
    if format == 'rio_antes_de_sair':
        lines = [build_script(snapshot)['narration']]
    elif format == 'chove_onde':
        topic = candidate['topic']
        metric, unit = {'temperatura':('max_c','graus'), 'vento':('wind_gust_max_kmh','quilômetros por hora'),
                        'chuva':('rain_probability_pct','por cento')} .get(topic, ('rain_mm', 'milímetros'))
        for loc in locs[:3]:
            value = loc.get(metric)
            if number(value):
                label = {'temperatura':'máxima', 'vento':'rajadas', 'chuva':'probabilidade de chuva no dia'}.get(topic,'volume previsto no dia')
                lines.append(f"Em {loc['name']}, {label} de {value:g} {unit}.")
            if loc.get('rain_window') and topic in {'chuva','janela_chuva'}:
                w = loc['rain_window']
                lines.append(f"Os horários com maior probabilidade aparecem entre {w['start']} e {w['end']}; pode haver intervalos sem chuva.")
        if topic in {'chuva','janela_chuva'}: lines.append('Probabilidade não indica chuva contínua durante todo o período.')
    elif format == 'fim_de_semana':
        for block in snapshot['forecast'].values():
            if not isinstance(block, dict) or block.get('date') not in candidate['extra']['dates']: continue
            values = [e for e in block['locations'] if number(e.get('max_c'))]
            if not values: raise ValueError('Fim de semana com dia sem dados')
            label = 'sábado' if stamp(block['date']+'T12:00:00-03:00').weekday()==5 else 'domingo'
            lines.append(f"No {label}, as máximas ficam entre {min(e['max_c'] for e in values):g} e {max(e['max_c'] for e in values):g} graus nos pontos consultados.")
        lines.append('Confira as próximas atualizações: o cenário pode mudar até o fim de semana.')
    elif format == 'vai_ao_jogo':
        event = candidate['extra']['event']; start,end = stamp(event['start_at']),stamp(event['end_at'])
        loc = locs[0]
        lines.append(f"Vai a {event['name']}? Confira a previsão para {loc['name']}.")
        for label, a, b in [('chegada',start-timedelta(hours=2),start),('evento',start,end),('saída',end,end+timedelta(hours=2))]:
            rows = [r for r in loc['hourly'] if a<=stamp(r['time'])<b and number(r.get('precipitation_probability'))]
            if not rows: raise ValueError(f'Sem previsão para a janela de {label}')
            lines.append(f"Na {label}, a maior probabilidade de chuva por hora é de {max(r['precipitation_probability'] for r in rows):g} por cento.")
    elif format == 'vai_dar_praia':
        # Exige vínculo por local; um status global não autoriza praia específica.
        sea = snapshot['marine'].get('data',{}).get('points',{})
        reports = snapshot['beach_status'].get('data',{}).get('points',{})
        for loc in locs[:2]:
            report = reports.get(loc['id'],{})
            if not report.get('source_url','').startswith('https://') or not report.get('valid_until'):
                raise ValueError('Boletim oficial da praia sem origem ou validade')
            current = stamp(candidate['created_at'])
            if stamp(report['valid_until'])<=current: raise ValueError('Boletim de praia vencido')
            wave = sea.get(loc['id'],{}).get('wave_height_max')
            if not number(wave): raise ValueError('Ondas indisponíveis para a praia')
            lines.append(f"Em {loc['name']}, ondas modeladas de até {wave:g} metros. O boletim oficial informa: {report.get('classification','não informada')}.")
        lines.append('A previsão do tempo não determina segurança para banho. Confira a sinalização e os avisos locais.')
    if not lines: raise ValueError('Nenhuma fala sustentada pelos dados')
    if candidate['language']=='probabilistic': lines.insert(0,'O cenário ainda tem incerteza. Há possibilidade de mudança.')
    if format!='rio_antes_de_sair': lines.append('Previsão RJ. Confira a atualização antes de sair.')
    beats=[{'fala':line,'legenda':line,'tipo':'nenhum','dados':{}} for line in lines]
    return {'title':TITLES[format], 'candidate':candidate,'beats':beats,'publication':False}

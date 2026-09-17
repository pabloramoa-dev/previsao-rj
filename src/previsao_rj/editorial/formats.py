"""Cinco formatos com validação de dados antes de produzir a fala."""
from datetime import timedelta
from .contrast import regional_contrast
from .cinco import cinco_regioes, fala_resumo
from .engine import evaluate, stamp
from .script import (build_script, decimal_br, em_local, em_locais,
                     faixa_escrita, faixa_falada, hora_agora, janela_legivel,
                     number, para_voz, pico_escrito, pico_falado)

TITLES = {'rio_antes_de_sair': 'RIO ANTES DE SAIR', 'chove_onde': 'O TEMPO MUDA ONDE?',
          'vai_dar_praia': 'VAI DAR PRAIA?', 'fim_de_semana': 'SEU FIM DE SEMANA', 'vai_ao_jogo': 'VAI AO JOGO?',
          'amanha_no_rio': 'AMANHÃ NO RIO'}


def batida(fala, tipo='nenhum', legenda=None, **dados):
    """`legenda` só difere da fala quando a tela pede forma curta ("23h")
    e a voz pede extenso ("vinte e três horas")."""
    return {'fala': para_voz(fala), 'legenda': decimal_br(legenda or fala),
            'tipo': tipo, 'dados': dados}


def rio_antes_de_sair(snapshot, incerto):
    """Batidas com cartao proprio, em vez de um paragrafo sobre o apresentador.

    O formato devolvia UMA fala com tipo 'nenhum': o render nao tinha o que
    desenhar e o Reel virava locucao sobre fundo parado. Agora cada informacao
    tem a sua batida e o seu cartao — e nenhuma batida nasce sem o dado que ela
    mostra, entao coleta incompleta encurta o Reel em vez de inventar numero.
    """
    dados = build_script(snapshot)
    locs = snapshot['forecast']['today']['locations']
    quente, frio, chuvoso = dados['hottest'], dados['coolest'], dados['wettest']
    contraste = regional_contrast(locs)
    # Abre SEM cartao de proposito. Gancho, resumo e CTA sao altos e tiram o
    # apresentador de cena; se todas as batidas fossem dessas, a locucao inteira
    # sairia sobre um cenario vazio. A abertura e o aviso de incerteza sao as
    # batidas em que ele aparece.
    batidas = [batida('Antes de sair de casa, veja como fica o tempo no Rio hoje.')]
    if incerto:
        batidas.append(batida('O cenário ainda tem incerteza. Há possibilidade de mudança.'))
    if contraste['temperature']['relevant']:
        vao = contraste['temperature']['spread']
        batidas.append(batida(
            f"Hoje a temperatura muda pela região: {vao:g} graus separam "
            f"{quente['name']} de {frio['name']}.",
            'gancho', numero=f'{vao:g}°', sub='DE DIFERENÇA NA REGIÃO'))
    else:
        batidas.append(batida(
            f"No Rio, a máxima prevista chega a {quente['max_c']:g} graus {em_local(quente['name'])}.",
            'gancho', numero=f"{quente['max_c']:g}°", sub='MÁXIMA PREVISTA HOJE'))
    resumo = batida_resumo(locs, 'HOJE NA REGIÃO')
    if resumo:
        batidas.append(resumo)
    if chuvoso:
        pct = chuvoso['rain_probability_pct']
        batidas.append(batida(
            f"{em_local(chuvoso['name'], inicio=True)}, a chance de chuva no dia é de {pct:g} por cento. "
            'Não significa chuva o dia inteiro.',
            'gancho', numero=f'{pct:g}%', sub='CHANCE DE CHUVA'))
    else:
        batidas.append(batida('A probabilidade de chuva não está disponível nesta coleta.'))
    if contraste['gust']['relevant']:
        alta = contraste['gust']['high']
        batidas.append(batida(
            f"Atenção ao vento: rajadas de até {alta['value']:g} quilômetros por hora "
            f"{em_local(alta['name'])}.",
            'alerta', titulo='VENTO', detalhe=f"até {alta['value']:g} km/h {em_local(alta['name'])}"))
    batidas.append(batida('Confira a atualização antes de sair. Previsão RJ.', 'cta'))
    return batidas


def amanha_no_rio(snapshot, incerto):
    """Reel da noite (Bia, 18h): como fica o tempo AMANHÃ.

    Mesma espinha do `rio_antes_de_sair`, lendo o bloco `tomorrow` do snapshot:
    abertura sem cartão, gancho de temperatura, as cinco previsões, chance de
    chuva, vento (se relevante) e o fecho. Nenhuma batida sem o dado dela.
    """
    bloco = snapshot['forecast'].get('tomorrow') or {}
    locs = bloco.get('locations') or []
    temps = [e for e in locs if number(e.get('max_c'))]
    if not temps:
        raise ValueError('Sem temperatura válida para amanhã')
    quente = max(temps, key=lambda e: e['max_c'])
    chuvas = [e for e in locs if number(e.get('rain_probability_pct'))]
    contraste = regional_contrast(locs)
    batidas = [batida('Amanhã, o tempo no Rio fica assim.')]
    if incerto:
        batidas.append(batida('O cenário para amanhã ainda tem incerteza. Pode mudar até de manhã.'))
    if contraste['temperature']['relevant']:
        alto, baixo = contraste['temperature']['high'], contraste['temperature']['low']
        vao = contraste['temperature']['spread']
        batidas.append(batida(
            f"A temperatura vai mudar pela região: {vao:g} graus separam "
            f"{alto['name']} de {baixo['name']}.",
            'gancho', numero=f'{vao:g}°', sub='DE DIFERENÇA AMANHÃ'))
    else:
        batidas.append(batida(
            f"A máxima chega a {quente['max_c']:g} graus {em_local(quente['name'])}.",
            'gancho', numero=f"{quente['max_c']:g}°", sub='MÁXIMA PREVISTA AMANHÃ'))
    # Sem repetir "amanhã" em toda frase: a abertura já disse, e o selo e os
    # cartões mostram AMANHÃ na tela.
    resumo = batida_resumo(locs, 'AMANHÃ NA REGIÃO')
    if resumo:
        batidas.append(resumo)
    if chuvas:
        molhado = max(chuvas, key=lambda e: e['rain_probability_pct'])
        pct = molhado['rain_probability_pct']
        batidas.append(batida(
            f"{em_local(molhado['name'], inicio=True)}, a chance de chuva amanhã é de {pct:g} por cento.",
            'gancho', numero=f'{pct:g}%', sub='CHANCE DE CHUVA AMANHÃ'))
    else:
        batidas.append(batida('A probabilidade de chuva para amanhã não está disponível nesta coleta.'))
    if contraste['gust']['relevant']:
        alta = contraste['gust']['high']
        batidas.append(batida(
            f"Atenção ao vento: rajadas de até {alta['value']:g} quilômetros por hora "
            f"{em_local(alta['name'])}.",
            'alerta', titulo='VENTO AMANHÃ',
            detalhe=f"até {alta['value']:g} km/h {em_local(alta['name'])}"))
    batidas.append(batida('Amanhã cedo tem atualização. Previsão RJ.', 'cta'))
    return batidas


def batida_resumo(locations, titulo, quando=''):
    """Cartão das cinco previsões obrigatórias (ver editorial/cinco.py)."""
    cidades = cinco_regioes(locations)
    if not cidades:
        return None
    return batida(fala_resumo(cidades, quando), 'resumo', cidades=cidades, titulo=titulo)


def prepare(snapshot, format='rio_antes_de_sair', reference=None, history=None, topic=None):
    """`topic` vem da pauta escolhida: sem ele, `chove_onde` podia desenhar
    'chuva' enquanto a legenda (que segue a pauta) falava de 'temperatura' —
    a fila usa histórico na nota e o render não."""
    options = [c for c in evaluate(snapshot, history, reference) if c['format'] == format and c['status'] == 'ready']
    if topic:
        options = [c for c in options if c['topic'] == topic]
    if not options:
        raise ValueError(f'Formato {format} (tópico {topic or "qualquer"}) sem candidato válido e atualizado')
    candidate = options[0]
    locs = [e for e in snapshot['forecast']['today']['locations'] if e['id'] in candidate['location_ids']]
    if format == 'rio_antes_de_sair':
        return {'title': TITLES[format], 'candidate': candidate, 'publication': False,
                'beats': rio_antes_de_sair(snapshot, candidate['language'] == 'probabilistic')}
    if format == 'amanha_no_rio':
        return {'title': TITLES[format], 'candidate': candidate, 'publication': False,
                'beats': amanha_no_rio(snapshot, candidate['language'] == 'probabilistic')}
    lines = []
    if format == 'chove_onde':
        topic = candidate['topic']
        metric, unit = {'temperatura':('max_c','graus'), 'vento':('wind_gust_max_kmh','quilômetros por hora'),
                        'chuva':('rain_probability_pct','por cento')} .get(topic, ('rain_mm', 'milímetros'))
        janelas = []   # (leitura, [nomes]) na ordem em que aparecem
        for loc in locs[:3]:
            value = loc.get(metric)
            if number(value):
                label = {'temperatura':'máxima', 'vento':'rajadas', 'chuva':'probabilidade de chuva no dia'}.get(topic,'volume previsto no dia')
                lines.append(f"{em_local(loc['name'], inicio=True)}, {label} de {value:g} {unit}.")
            if loc.get('rain_window') and topic in {'chuva','janela_chuva'}:
                leitura = janela_legivel(loc['rain_window'], hora_agora())
                if not leitura:
                    continue
                grupo = next((g for g in janelas if g[0] == leitura), None)
                if grupo:
                    grupo[1].append(loc['name'])
                else:
                    janelas.append((leitura, [loc['name']]))
        # Uma frase por horário, com todos os bairros que o compartilham: o
        # Reel de 15/09/2026 repetia "das vinte e uma às vinte e três horas"
        # bairro a bairro.
        for leitura, nomes in janelas:
            onde = em_locais(nomes, inicio=True)
            if leitura['tipo'] == 'faixa':
                resto = '; pode haver intervalos sem chuva.'
                lines.append((
                    f"{onde}, a chuva é mais provável "
                    + faixa_falada(leitura['inicio'], leitura['fim']) + resto,
                    f"{onde}, a chuva é mais provável "
                    + faixa_escrita(leitura['inicio'], leitura['fim']) + resto))
            else:
                resto = (f", com {leitura['probabilidade']:g} por cento; "
                         'pode haver intervalos sem chuva.')
                lines.append((
                    f"{onde}, a maior probabilidade é " + pico_falado(leitura['hora']) + resto,
                    f"{onde}, a maior probabilidade é " + pico_escrito(leitura['hora']) + resto))
        if topic in {'chuva','janela_chuva'}: lines.append('Probabilidade não indica chuva contínua durante todo o período.')
    elif format == 'fim_de_semana':
        for block in snapshot['forecast'].values():
            if not isinstance(block, dict) or block.get('date') not in candidate['extra']['dates']: continue
            values = [e for e in block['locations'] if number(e.get('max_c'))]
            if not values: raise ValueError('Fim de semana com dia sem dados')
            # A faixa de máximas de cada dia sai no cartão das cinco previsões
            # (resumo), inserido abaixo — repetir aqui dobraria a mesma frase.
        lines.append('Confira as próximas atualizações: o cenário pode mudar até o fim de semana.')
    elif format == 'vai_ao_jogo':
        event = candidate['extra']['event']; start,end = stamp(event['start_at']),stamp(event['end_at'])
        loc = locs[0]
        lines.append(f"Vai a {event['name']}? Confira a previsão para {loc['name']}.")
        for label, a, b in [('chegada',start-timedelta(hours=2),start),('evento',start,end),('saída',end,end+timedelta(hours=2))]:
            all_rows = [r for block in snapshot['forecast'].values() if isinstance(block,dict)
                        for e in block.get('locations',[]) if e['id']==loc['id'] for r in e.get('hourly',[])]
            rows = [r for r in all_rows if a<=stamp(r['time'])<b and number(r.get('precipitation_probability'))]
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
            point=sea.get(loc['id'],{})
            if point.get('date')!=snapshot['forecast']['today'].get('date'): raise ValueError('Ondas fora da data consultada')
            wave = point.get('wave_height_max')
            if not number(wave): raise ValueError('Ondas indisponíveis para a praia')
            lines.append(f"{em_local(loc['name'], inicio=True)}, ondas modeladas de até {wave:g} metros. O boletim oficial informa: {report.get('classification','não informada')}.")
        lines.append('A previsão do tempo não determina segurança para banho. Confira a sinalização e os avisos locais.')
    if not lines: raise ValueError('Nenhuma fala sustentada pelos dados')
    if candidate['language']=='probabilistic': lines.insert(0,'O cenário ainda tem incerteza. Há possibilidade de mudança.')
    lines.append('Previsão RJ. Confira a atualização antes de sair.')
    beats=[batida(line[0], legenda=line[1]) if isinstance(line, tuple) else batida(line) for line in lines]
    # Todo Reel mostra as cinco previsões obrigatórias, antes do fecho.
    resumos = []
    if format == 'fim_de_semana':
        for block in snapshot['forecast'].values():
            if not isinstance(block, dict) or block.get('date') not in candidate['extra']['dates']:
                continue
            dia = 'SÁBADO' if stamp(block['date']+'T12:00:00-03:00').weekday()==5 else 'DOMINGO'
            resumos.append(batida_resumo(block['locations'], f'{dia} NA REGIÃO', f'No {dia.lower()}'))
        # Os dias vêm antes do aviso de que o cenário pode mudar.
        posicao = len(beats) - 2
    else:
        resumos.append(batida_resumo(snapshot['forecast']['today']['locations'], 'HOJE NA REGIÃO'))
        posicao = len(beats) - 1
    for r in reversed(resumos):
        if r:
            beats.insert(max(posicao, 0), r)
    if format == 'fim_de_semana' and beats[0]['tipo'] == 'resumo':
        # Abre sem cartão (o apresentador precisa aparecer na primeira batida).
        beats.insert(0, batida('Veja como fica o fim de semana no Rio.'))
    return {'title':TITLES[format], 'candidate':candidate,'beats':beats,'publication':False}

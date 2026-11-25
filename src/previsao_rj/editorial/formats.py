"""Cinco formatos com validação de dados antes de produzir a fala."""
from datetime import date, timedelta
from .contrast import regional_contrast
from .cinco import cinco_regioes, fala_resumo
from .engine import evaluate, stamp
from .script import (build_script, decimal_br, em_local, em_locais,
                     faixa_escrita, faixa_falada, hora_agora, janela_legivel,
                     number, para_voz, pico_escrito, pico_falado)

TITLES = {'rio_antes_de_sair': 'RIO ANTES DE SAIR', 'chove_onde': 'O TEMPO MUDA ONDE?',
          'vai_dar_praia': 'VAI DAR PRAIA?', 'fim_de_semana': 'SEU FIM DE SEMANA', 'vai_ao_jogo': 'VAI AO JOGO?',
          'amanha_no_rio': 'AMANHÃ NO RIO'}



def gancho_rotativo(locs, data, quando, *, ancora=None, canal=""):
    """Gancho de retenção por edição, com fatos validados e sem alarmismo."""
    from datetime import date, timedelta
    from math import isfinite
    def num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)
    def valor(c, *keys):
        return next((c[k] for k in keys if num(c.get(k))), None)
    def nome(c):
        return c.get("name") or c.get("nome") or c.get("point")
    validos = [c for c in locs if nome(c) and valor(c, "max_c", "max") is not None]
    if not validos:
        return "Confira a previsão " + quando + "."
    try:
        dia = date.fromisoformat(str(data)[:10])
    except (ValueError, TypeError):
        dia = date.today()
    noite = quando == "amanhã"
    pub = dia - timedelta(days=int(noite))
    fase = sum(ord(ch) for ch in canal) % 12
    slot = pub.toordinal() * 2 + int(noite) + fase
    c = ancora if ancora in validos else validos[(slot // 2 + int(noite)) % len(validos)]
    n = nome(c)
    mx = round(valor(c, "max_c", "max"))
    mn0 = valor(c, "min_c", "min")
    mn = round(mn0) if mn0 is not None else None
    outros = [x for x in validos if nome(x) != n]
    outro = max(outros, key=lambda x: abs(valor(x, "max_c", "max") - mx), default=None)
    dif = round(valor(outro, "max_c", "max")) if outro else mx
    fato = f"{n}: {mx} graus {quando}."
    faixa = f"{n}: de {mn} a {mx} graus {quando}." if mn is not None else fato
    # 12 famílias: identificação, curiosidade, antecipação, contraste,
    # proteção, urgência, surpresa, pergunta, comparação, benefício,
    # informação específica e expectativa. Condições especiais têm gate.
    familias = {
        0: (f"Mora em {n}? {mx} graus {quando}.", f"Alô, {n}! Máxima de {mx} graus {quando}.", fato, f"{n}, sua máxima: {mx} graus {quando}."),
        1: (f"Quanto vai fazer em {n}? {mx} graus {quando}.", f"{n}: sabe qual a máxima {quando}? {mx} graus.", f"{fato} E na sua cidade?", f"{n}: como fica {quando}? {mx} graus."),
        2: (f"Planeje {quando}: {faixa}", f"Já se programe: {faixa}", f"Para {quando}, {faixa}", f"Antecipe seus planos: {fato}"),
        4: (f"Antes de sair, {fato}", f"Vai sair em {n}? {mx} graus {quando}.", f"Prepare-se: {faixa}", f"De olho na temperatura: {fato}"),
        7: (f"Vai fazer calor em {n}? {mx} graus {quando}.", f"Casaco ou roupa leve? {faixa}", f"Vai sair {quando}? {faixa}", f"Como se vestir em {n}? {faixa}"),
        8: (f"Compare as temperaturas: {fato}", f"Veja os números: {fato}", f"De cidade em cidade: {fato}", f"Compare com a sua rotina: {faixa}"),
        9: (f"Organize seu dia: {faixa}", f"Para planejar a rotina: {fato}", f"Seu dia em {n}: {mx} graus {quando}.", f"Programe sua saída: {fato}"),
        10: (fato, f"Máxima de {mx} graus em {n} {quando}.", faixa, f"{quando.capitalize()}, {n} pode chegar a {mx} graus."),
        11: (f"{fato} E as demais cidades?", f"{fato} Veja as outras temperaturas.", f"Começando por {n}: {mx} graus {quando}.", f"Primeiro, {fato}"),
    }
    if mn is not None and mx - mn >= 7:
        familias[3] = (f"De {mn} a {mx} graus em {n} {quando}.", f"{n}: mínima de {mn}, máxima de {mx} {quando}.", faixa, f"Do mínimo de {mn} ao máximo de {mx} graus em {n} {quando}.")
    if outro and abs(dif - mx) >= 4:
        familias[6] = (f"{n}: {mx} graus. {nome(outro)}: {dif} {quando}.", f"Olha a diferença {quando}: {n}, {mx}; {nome(outro)}, {dif} graus.", f"Temperaturas bem diferentes: {n}, {mx}; {nome(outro)}, {dif} graus {quando}.", f"{n} e {nome(outro)}: {mx} e {dif} graus {quando}.")
        familias[8] = familias[6][::-1]
    rajada = valor(c, "gust_kmh", "wind_gust_kmh", "rajada_kmh")
    if rajada is not None and rajada >= 60:
        familias[5] = (f"Atenção em {n}: rajadas fortes {quando}.", f"Vento forte previsto em {n} {quando}.", f"{n}: cuidado com as rajadas {quando}.", f"De olho no vento forte em {n} {quando}.")
    elif mx >= 38:
        familias[5] = (f"Atenção em {n}: máxima de {mx} graus {quando}.", f"{n}: calor intenso, {mx} graus {quando}.", f"Cuidado com o calor em {n}: {mx} graus {quando}.", f"{mx} graus previstos em {n} {quando}: cuide-se.")
    # Se um fenômeno não existe, mantém a alternância sem fabricar o fato.
    k = slot % 12
    fallback = {3: 9, 5: 11, 6: 0}
    k = k if k in familias else fallback.get(k, 10)
    return familias[k][(slot // 12) % 4]


def engajamento_rotativo(data, quando, local="", canal=""):
    """Um pedido útil por edição, com rodízio independente do gancho."""
    from datetime import date, timedelta
    try:
        dia = date.fromisoformat(str(data)[:10])
    except (ValueError, TypeError):
        dia = date.today()
    noite = quando == "amanhã"
    pub = dia - timedelta(days=int(noite))
    slot = pub.toordinal() * 2 + int(noite) + sum(ord(ch) for ch in canal)
    familias = (
        ("Envie a previsão a quem vai sair.", "Compartilhe com quem mora na região.", "Manda pra quem precisa dessa previsão.", "Envie para quem vai viajar."),
        ("Qual sua cidade? Comente aqui.", "Como está o tempo aí? Comente.", "De qual bairro você nos acompanha?", "Qual cidade quer ver por aqui?"),
        ("Salve para consultar antes de sair.", "Guarde esta previsão para seu dia.", "Salve o boletim para planejar.", "Salve para conferir mais tarde."),
        ("Siga para acompanhar a previsão diária.", "Siga e acompanhe o tempo na região.", "Acompanhe o perfil para novos boletins.", "Siga para conferir a próxima previsão."),
    )
    return familias[slot % len(familias)][(slot // len(familias)) % 4]


def batida(fala, tipo='nenhum', legenda=None, **dados):
    """`legenda` só difere da fala quando a tela pede forma curta ("23h")
    e a voz pede extenso ("vinte e três horas")."""
    return {'fala': para_voz(fala), 'legenda': decimal_br(legenda or fala),
            'tipo': tipo, 'dados': dados}



def destaque_da_semana(snapshot, locations):
    """Destaques por DIA DE PUBLICAÇÃO, nunca pela data de amanhã.

    São Gonçalo: segundas e quintas (segunda oportunidade na semana).
    Icaraí, Niterói: terças e sábados. Se a coleta não trouxer mínima e
    máxima válidas, não cita uma previsão sem dados.
    """
    try:
        dia = date.fromisoformat(snapshot['forecast']['today']['date']).weekday()
    except (KeyError, ValueError, TypeError):
        return None
    local_id = {0: 'sao_goncalo', 3: 'sao_goncalo',
                1: 'icarai', 5: 'icarai'}.get(dia)
    return next((loc for loc in locations
                 if loc.get('id') == local_id
                 and number(loc.get('min_c')) and number(loc.get('max_c'))), None) if local_id else None


def gancho_destaque(snapshot, locations, periodo):
    """Gancho hiperlocal protegido contra corte; substitui o gancho térmico.

    Mantém a duração do Reel e deixa intacto o resumo das seis regiões.
    """
    local = destaque_da_semana(snapshot, locations)
    if local is None:
        return None
    icarai = local['id'] == 'icarai'
    onde = 'em Icaraí, Niterói' if icarai else 'em São Gonçalo'
    selo = 'ICARAÍ · NITERÓI' if icarai else 'SÃO GONÇALO'
    periodo_na_tela = 'HOJE' if periodo == 'hoje' else 'AMANHÃ'
    # A abertura noturna já diz 'amanhã'; não repetir na narração.
    inicio = 'Hoje, ' if periodo == 'hoje' else ''
    lugar = onde if inicio else onde[0].upper() + onde[1:]
    fala = (f"{inicio}{lugar}: mínima de {local['min_c']:g} e "
            f"máxima de {local['max_c']:g} graus.")
    return batida(fala, 'gancho', numero=f"{local['max_c']:g}°",
                  sub=f"{selo} · {periodo_na_tela}", destaque_local=True)


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
    # sairia sobre um cenario vazio. A abertura mostra o apresentador.
    batidas = [batida(gancho_rotativo(locs, snapshot['forecast']['today'].get('date'), 'hoje', ancora=destaque_da_semana(snapshot, locs), canal="previsao-rj"))]
    destaque = gancho_destaque(snapshot, locs, 'hoje')
    if destaque is not None:
        batidas.append(destaque)
    elif contraste['temperature']['relevant']:
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
    batidas.append(batida(engajamento_rotativo(snapshot['forecast']['today'].get('date'), 'hoje', canal="previsao-rj"), 'cta'))
    return batidas


def amanha_no_rio(snapshot, incerto):
    """Reel da noite (Bia, 18h): como fica o tempo AMANHÃ.

    Mesma espinha do `rio_antes_de_sair`, lendo o bloco `tomorrow` do snapshot:
    abertura sem cartão, gancho de temperatura, as seis previsões, chance de
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
    batidas = [batida(gancho_rotativo(locs, bloco.get('date'), 'amanhã', ancora=destaque_da_semana(snapshot, locs), canal="previsao-rj"))]
    destaque = gancho_destaque(snapshot, locs, 'amanha')
    if destaque is not None:
        batidas.append(destaque)
    elif contraste['temperature']['relevant']:
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
    batidas.append(batida(engajamento_rotativo(bloco.get('date'), 'amanhã', canal="previsao-rj"), 'cta'))
    return batidas


def batida_resumo(locations, titulo, quando=''):
    """Cartão das seis previsões obrigatórias (ver editorial/cinco.py)."""
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
    # A confiança dos dados controla os vetos e a linguagem no motor editorial;
    # não acrescentar aviso genérico de incerteza à abertura do vídeo.
    destinatario = {'vai_dar_praia': 'vai à praia', 'fim_de_semana': 'vai passear no fim de semana'}.get(format, 'vai sair no Rio')
    lines.append(f'Manda pra quem {destinatario}.')
    beats=[batida(line[0], legenda=line[1]) if isinstance(line, tuple) else batida(line) for line in lines]
    # Todo Reel mostra as seis previsões obrigatórias, antes do fecho.
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

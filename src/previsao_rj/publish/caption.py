"""Legenda do Reel — amarrada a pauta que foi ao ar.

Ate aqui a legenda saia so do snapshot: sempre o mesmo texto de contraste, nao
importava o formato renderizado nem o item que o publicador marcava como
publicado. Video, legenda e fila decidiam coisas diferentes, e o historico
editorial passou a registrar pauta que ninguem viu — o que desarma justamente
os vetos de duplicata e de gancho repetido que a fila existe para armar.

Agora a pauta escolhida manda nos tres. Sem item, o texto antigo continua
valendo, para nao quebrar chamada sem fila.

Regra dura mantida: a legenda sempre termina com a assinatura @previsaorj, que
`publish.cli` confere antes de falar com a Meta.
"""
from __future__ import annotations

from typing import Any

from ..geo.preposicao import em_local

ASSINATURA = '@previsaorj — O tempo do Rio para decidir seu dia.'

HASHTAGS = {
    'rio_antes_de_sair': '#PrevisaoRJ #RioDeJaneiro #TempoRJ',
    'chove_onde': '#PrevisaoRJ #ChuvaNoRio #TempoRJ',
    'fim_de_semana': '#PrevisaoRJ #FimDeSemana #RioDeJaneiro',
    'vai_dar_praia': '#PrevisaoRJ #PraiaNoRio #RioDeJaneiro',
    'vai_ao_jogo': '#PrevisaoRJ #RioDeJaneiro #TempoRJ',
}
HASHTAGS_PADRAO = '#PrevisaoRJ #RioDeJaneiro #TempoRJ'

FECHO = {
    'rio_antes_de_sair': 'Confira a atualização antes de sair.',
    'chove_onde': 'Probabilidade não é chuva o dia inteiro. Confira antes de sair.',
    'fim_de_semana': 'O cenário ainda pode mudar até lá. Confira as próximas atualizações.',
    'vai_dar_praia': 'A previsão não determina segurança para banho. Siga a sinalização local.',
    'vai_ao_jogo': 'Saia de casa preparado para as três janelas: chegada, jogo e volta.',
}


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _g(value: Any) -> str:
    return f'{value:g}'


def _names(snapshot: dict) -> dict[str, str]:
    """id -> nome, varrendo todos os dias do snapshot.

    O item da fila guarda id; quem le a legenda le nome de bairro.
    """
    names: dict[str, str] = {}
    for block in (snapshot.get('forecast') or {}).values():
        if not isinstance(block, dict):
            continue
        for entry in block.get('locations', []) or []:
            if entry.get('id') and entry.get('name'):
                names.setdefault(entry['id'], entry['name'])
    return names


def _today(snapshot: dict) -> list[dict]:
    return (snapshot.get('forecast', {}).get('today', {}) or {}).get('locations', []) or []


def _linhas_rio_antes_de_sair(snapshot: dict, item: dict, names: dict) -> list[str]:
    locs = [e for e in _today(snapshot) if _num(e.get('max_c'))]
    if not locs:
        return []
    quente = max(locs, key=lambda e: e['max_c'])
    frio = min(locs, key=lambda e: e['max_c'])
    chuvosos = [e for e in _today(snapshot) if _num(e.get('rain_probability_pct'))]
    linhas = [f"🌡️ Máximas entre {_g(frio['max_c'])}° {em_local(frio['name'])} "
              f"e {_g(quente['max_c'])}° {em_local(quente['name'])}"]
    if chuvosos:
        molhado = max(chuvosos, key=lambda e: e['rain_probability_pct'])
        linhas.append(f"☔ Maior chance de chuva: {molhado['name']}, "
                      f"{_g(molhado['rain_probability_pct'])}%")
    ventosos = [e for e in _today(snapshot) if _num(e.get('wind_gust_max_kmh'))]
    if ventosos:
        vento = max(ventosos, key=lambda e: e['wind_gust_max_kmh'])
        if vento['wind_gust_max_kmh'] >= 30:
            linhas.append(f"💨 Rajadas de até {_g(vento['wind_gust_max_kmh'])} km/h "
                          f"em {vento['name']}")
    return linhas


# topico -> (icone, rotulo, unidade, campo do snapshot)
#
# Cada topico le o SEU campo. Nao existe campo padrao: em 15/09/2026 a legenda
# de um `janela_chuva` saiu como "previsao de 22" — o 22 era a maxima em graus,
# rotulada como se fosse o volume de chuva da pauta. Faltando o dado do topico,
# a linha nao entra; numero de outra grandeza e pior do que linha nenhuma.
MEDIDAS = {
    'temperatura': ('🌡️', 'máxima', '°', 'max_c'),
    'chuva': ('☔', 'chance de chuva', '%', 'rain_probability_pct'),
    'vento': ('💨', 'rajadas de até', ' km/h', 'wind_gust_max_kmh'),
    'janela_chuva': ('🌧️', 'volume previsto', ' mm', 'rain_mm'),
}


def _por_id(snapshot: dict) -> dict[str, dict]:
    return {e['id']: e for e in _today(snapshot) if e.get('id')}


def _valor(snapshot: dict, item: dict, local_id: str, campo: str):
    """Valor do campo pedido: snapshot primeiro, `facts` do item como reserva.

    O snapshot tem todos os campos; `facts` guarda só três (máxima, chance de
    chuva e rajada), então volume de chuva, por exemplo, só existe no snapshot.
    """
    entrada = _por_id(snapshot).get(local_id, {})
    valor = entrada.get(campo)
    if not _num(valor):
        valor = (item.get('facts') or {}).get(local_id, {}).get(campo)
    return valor if _num(valor) else None


def _linhas_chove_onde(snapshot: dict, item: dict, names: dict) -> list[str]:
    topico = item.get('topic')
    if topico not in MEDIDAS:
        return []
    icone, rotulo, unidade, campo = MEDIDAS[topico]

    contraste = (item.get('extra') or {}).get('contrast') or {}
    alto, baixo = contraste.get('high') or {}, contraste.get('low') or {}
    if _num(alto.get('value')) and _num(baixo.get('value')):
        linhas = [f"{icone} {alto['name']}: {rotulo} {_g(alto['value'])}{unidade}",
                  f"{icone} {baixo['name']}: {rotulo} {_g(baixo['value'])}{unidade}"]
        if _num(contraste.get('spread')):
            linhas.append(f"↔️ {_g(contraste['spread'])}{unidade} de diferença "
                          'entre as duas pontas do Rio hoje')
        return linhas

    linhas = []
    for local_id in item.get('location_ids', [])[:3]:
        valor = _valor(snapshot, item, local_id, campo)
        if valor is None:
            continue
        linhas.append(f"{icone} {names.get(local_id, local_id)}: "
                      f"{rotulo} {_g(valor)}{unidade}")

    # A hora é o que essa pauta tem de mais útil — desde que seja uma hora, e
    # não o dia inteiro travestido de recorte. `janela_legivel` decide isso.
    if topico == 'janela_chuva' and linhas:
        from ..editorial.script import hora_agora, janela_legivel
        agora = hora_agora()
        for local_id in item.get('location_ids', [])[:3]:
            leitura = janela_legivel(
                _por_id(snapshot).get(local_id, {}).get('rain_window'), agora)
            if not leitura:
                continue
            onde = names.get(local_id, local_id)
            if leitura['tipo'] == 'faixa':
                linhas.append(f"🕒 Maior chance entre {leitura['inicio']} e "
                              f"{leitura['fim']} {em_local(onde)}")
            else:
                linhas.append(f"🕒 Pico por volta das {leitura['hora']}, "
                              f"{_g(leitura['probabilidade'])}% {em_local(onde)}")
            break
    return linhas


def _linhas_fim_de_semana(snapshot: dict, item: dict, names: dict) -> list[str]:
    extra = item.get('extra') or {}
    previsao = extra.get('forecast') or {}
    linhas: list[str] = []
    for data in extra.get('dates', []) or []:
        pontos = [e for e in previsao.get(data, []) if _num(e.get('max_c'))]
        if not pontos:
            continue
        menor = min(e['max_c'] for e in pontos)
        maior = max(e['max_c'] for e in pontos)
        dia, mes = data[8:10], data[5:7]
        linhas.append(f"📅 {dia}/{mes}: máximas entre {_g(menor)}° e {_g(maior)}°")
        molhados = [e for e in pontos if _num(e.get('rain_probability_pct'))]
        if molhados:
            pior = max(molhados, key=lambda e: e['rain_probability_pct'])
            linhas.append(f"   ☔ maior chance de chuva em "
                          f"{names.get(pior.get('id'), pior.get('id'))}, "
                          f"{_g(pior['rain_probability_pct'])}%")
    return linhas


def _linhas_vai_dar_praia(snapshot: dict, item: dict, names: dict) -> list[str]:
    linhas: list[str] = []
    for local_id in item.get('location_ids', [])[:3]:
        fatos = (item.get('facts') or {}).get(local_id, {})
        nome = names.get(local_id, local_id)
        if _num(fatos.get('max_c')):
            parte = f"🏖️ {nome}: até {_g(fatos['max_c'])}°"
            if _num(fatos.get('rain_probability_pct')):
                parte += f", {_g(fatos['rain_probability_pct'])}% de chance de chuva"
            linhas.append(parte)
    return linhas


def _linhas_vai_ao_jogo(snapshot: dict, item: dict, names: dict) -> list[str]:
    evento = (item.get('extra') or {}).get('event') or {}
    linhas: list[str] = []
    if evento.get('name'):
        linhas.append(f"⚽ {evento['name']}")
    for local_id in item.get('location_ids', [])[:2]:
        fatos = (item.get('facts') or {}).get(local_id, {})
        if _num(fatos.get('rain_probability_pct')):
            linhas.append(f"☔ {names.get(local_id, local_id)}: "
                          f"{_g(fatos['rain_probability_pct'])}% de chance de chuva no dia")
    return linhas


CORPO = {
    'rio_antes_de_sair': _linhas_rio_antes_de_sair,
    'chove_onde': _linhas_chove_onde,
    'fim_de_semana': _linhas_fim_de_semana,
    'vai_dar_praia': _linhas_vai_dar_praia,
    'vai_ao_jogo': _linhas_vai_ao_jogo,
}

ABERTURA = {
    'rio_antes_de_sair': 'Como fica o tempo no Rio hoje, antes de você sair de casa.',
    'chove_onde': 'O tempo muda de bairro para bairro no Rio hoje.',
    'fim_de_semana': 'Seu fim de semana no Rio, Niterói e Baixada.',
    'vai_dar_praia': 'Vai dar praia hoje?',
    'vai_ao_jogo': 'Vai ao jogo? Veja como fica o tempo nas três janelas.',
}


def _legenda_antiga(snapshot: dict) -> str:
    """Texto usado ate 13/09/2026. Mantido para chamada sem pauta."""
    locs = snapshot['forecast']['today']['locations']
    hot = max(locs, key=lambda x: x['max_c'])
    cool = min(locs, key=lambda x: x['max_c'])
    wet = max(locs, key=lambda x: x.get('rain_probability_pct', 0))
    return (f"Hoje o Rio pode ter contrastes importantes entre as regiões.\n\n"
            f"🌡️ {hot['name']}: até {hot['max_c']}°\n"
            f"🌤️ {cool['name']}: até {cool['max_c']}°\n"
            f"☔ {wet['name']}: maior chance de chuva da amostra, "
            f"{wet.get('rain_probability_pct', 0)}%\n\n"
            "Confira a atualização antes de sair.\n\n"
            f"{ASSINATURA}\n\n"
            f"{HASHTAGS_PADRAO}")


def build_caption(snapshot: dict, item: dict | None = None) -> str:
    """Legenda do Reel. Com `item`, o texto segue a pauta que foi renderizada.

    Se a pauta nao sustentar nenhuma linha com dado — coleta incompleta, por
    exemplo — a legenda encurta em vez de inventar numero, e no limite volta ao
    texto geral do dia. Nunca sai legenda com campo vazio.
    """
    if not item:
        return _legenda_antiga(snapshot)

    formato = item.get('format', 'rio_antes_de_sair')
    names = _names(snapshot)
    linhas = CORPO.get(formato, _linhas_rio_antes_de_sair)(snapshot, item, names)
    if not linhas:
        linhas = _linhas_rio_antes_de_sair(snapshot, item, names)
    if not linhas:
        return _legenda_antiga(snapshot)

    partes = [ABERTURA.get(formato, ABERTURA['rio_antes_de_sair']),
              '',
              '\n'.join(linhas),
              '',
              FECHO.get(formato, FECHO['rio_antes_de_sair']),
              '',
              ASSINATURA,
              '',
              HASHTAGS.get(formato, HASHTAGS_PADRAO)]
    return '\n'.join(partes)

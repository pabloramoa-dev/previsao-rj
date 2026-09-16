"""Roteiros ancorados nos valores disponíveis, sem contraste inventado."""
from __future__ import annotations
import math
import re
from .contrast import regional_contrast
from ..geo.preposicao import em_local, em_locais  # noqa: F401  (reexportado)


def number(value):
    return isinstance(value, (float, int)) and math.isfinite(value)


def build_script(snapshot: dict) -> dict:
    locs = snapshot["forecast"]["today"]["locations"]
    temps = [e for e in locs if number(e.get("max_c"))]
    rains = [e for e in locs if number(e.get("rain_probability_pct"))]
    if not temps:
        raise ValueError("Sem temperatura válida para o roteiro")
    hottest = max(temps, key=lambda x: x["max_c"])
    coolest = min(temps, key=lambda x: x["max_c"])
    wettest = max(rains, key=lambda x: x["rain_probability_pct"]) if rains else None
    contrast = regional_contrast(locs)
    if contrast["temperature"]["relevant"]:
        hook = "A TEMPERATURA MUDA PELA REGIÃO"
        text = (f"No Rio, {hottest['name']} tem máxima prevista de {hottest['max_c']:g} graus. "
                f"{em_local(coolest['name'], inicio=True)}, são {coolest['max_c']:g} graus. ")
    else:
        hook = "RIO ANTES DE SAIR"
        text = (f"No Rio, as máximas previstas ficam entre {coolest['max_c']:g} "
                f"e {hottest['max_c']:g} graus nos pontos consultados. ")
    if contrast["gust"]["relevant"]:
        high = contrast["gust"]["high"]
        text += f"Atenção ao vento: rajadas previstas de até {high['value']:g} quilômetros por hora {em_local(high['name'])}. "
    if wettest:
        text += (f"{em_local(wettest['name'], inicio=True)}, a probabilidade de chuva no dia é de "
                 f"{wettest['rain_probability_pct']:g} por cento. Isso não significa chuva o dia inteiro. ")
    else:
        text += "A probabilidade de chuva não está disponível nesta coleta. "
    text += "Confira a atualização antes de sair. Previsão RJ. O tempo do Rio para decidir seu dia."
    return {"hook": hook, "narration": text, "hottest": hottest, "coolest": coolest, "wettest": wettest}


# Janela larga nao informa nada. Em 15/09/2026 o Reel e a legenda anunciaram
# "maior chance entre 00:00 e 23:00": tecnicamente verdadeiro, editorialmente
# inutil — o dia inteiro anunciado como se fosse um recorte. Quando a janela
# passa de LARGA_H horas, o que informa e o PICO, que o snapshot ja calcula.
LARGA_H = 8


def _hora(texto):
    try:
        return int(str(texto).split(':')[0])
    except (ValueError, AttributeError, IndexError):
        return None


def janela_legivel(janela: dict | None, agora: int | None = None) -> dict | None:
    """Traduz `rain_window` no que vale dizer: faixa estreita ou hora do pico.

    `agora` e a hora cheia atual (0-23). Com ela, o que ja passou nao e dito: o
    Reel sai as 6h e anunciar "pico por volta das 01:00" e informar chuva de
    ontem a noite para quem esta decidindo se leva guarda-chuva hoje. Janela que
    terminou fica de fora; janela que comecou antes do amanhecer e cortada no
    agora e so o que resta dela e anunciado.

    Devolve `None` quando nao ha nada confiavel a dizer — e ai a linha nao entra,
    em vez de anunciar o dia inteiro, ou o passado, como se fosse um horario.
    """
    if not isinstance(janela, dict):
        return None
    inicio, fim = janela.get('start'), janela.get('end')
    h_inicio, h_fim = _hora(inicio), _hora(fim)
    if h_inicio is None or h_fim is None or h_fim <= h_inicio:
        return None

    if agora is not None:
        if h_fim <= agora:
            return None
        if h_inicio < agora:
            h_inicio, inicio = agora, f'{agora:02d}:00'

    if h_fim - h_inicio < LARGA_H:
        return {'tipo': 'faixa', 'inicio': inicio, 'fim': fim}

    pico = janela.get('peak_hour')
    prob = janela.get('peak_probability_pct')
    h_pico = _hora(pico)
    if pico and number(prob) and (agora is None or (h_pico is not None and h_pico >= agora)):
        return {'tipo': 'pico', 'hora': pico, 'probabilidade': prob}
    return None


# ------------------------------------------------------- hora para a voz

# O Kokoro le "23:00" como "vinte e tres zero zero" (Reel de 15/09/2026). A fala
# recebe a hora por extenso, com artigo e crase certos; a legenda na tela fica
# com a forma curta ("23h"), que se le num relance.
_HORAS = ['zero', 'uma', 'duas', 'três', 'quatro', 'cinco', 'seis', 'sete',
          'oito', 'nove', 'dez', 'onze', 'doze', 'treze', 'catorze', 'quinze',
          'dezesseis', 'dezessete', 'dezoito', 'dezenove', 'vinte',
          'vinte e uma', 'vinte e duas', 'vinte e três']
_MINUTOS = {15: 'quinze', 30: 'trinta', 45: 'quarenta e cinco'}
_DE = {'a': 'da', 'as': 'das', 'o': 'do'}
_A = {'a': 'à', 'as': 'às', 'o': 'ao'}


def _partes(texto):
    try:
        h, m = (int(x) for x in str(texto).split(':')[:2])
    except (ValueError, AttributeError):
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h, m


def _falada(texto, com_unidade=True):
    """(artigo, expressão) — ('as', 'vinte e três horas'), ('o', 'meio-dia')."""
    partes = _partes(texto)
    if partes is None:
        return None
    h, m = partes
    if m == 0 and h == 0:
        return 'a', 'meia-noite'
    if m == 0 and h == 12:
        return 'o', 'meio-dia'
    artigo = 'a' if h == 1 else 'as'
    if m:
        return artigo, f"{_HORAS[h]} e {_MINUTOS.get(m, m)}"
    unidade = (' hora' if h == 1 else ' horas') if com_unidade else ''
    return artigo, _HORAS[h] + unidade


def hora_escrita(texto) -> str:
    """'23:00' -> '23h'; '19:30' -> '19h30'; 0h e 12h viram meia-noite e meio-dia."""
    partes = _partes(texto)
    if partes is None:
        return str(texto)
    h, m = partes
    if m == 0 and h in (0, 12):
        return 'meia-noite' if h == 0 else 'meio-dia'
    return f'{h}h{m:02d}' if m else f'{h}h'


def faixa_falada(inicio, fim) -> str:
    """'20:00', '23:00' -> 'das vinte às vinte e três horas'."""
    fim_ = _falada(fim)
    ini_ = _falada(inicio, com_unidade=not (fim_ and fim_[0] == 'as'))
    if ini_ is None or fim_ is None:
        return f'entre {inicio} e {fim}'
    return f"{_DE[ini_[0]]} {ini_[1]} {_A[fim_[0]]} {fim_[1]}"


def faixa_escrita(inicio, fim) -> str:
    ini_, fim_ = _falada(inicio), _falada(fim)
    if ini_ is None or fim_ is None:
        return f'entre {inicio} e {fim}'
    return f"{_DE[ini_[0]]} {hora_escrita(inicio)} {_A[fim_[0]]} {hora_escrita(fim)}"


def pico_falado(hora) -> str:
    """'19:00' -> 'por volta das dezenove horas'."""
    h = _falada(hora)
    return f"por volta {_DE[h[0]]} {h[1]}" if h else f'por volta das {hora}'


def pico_escrito(hora) -> str:
    h = _falada(hora)
    return f"por volta {_DE[h[0]]} {hora_escrita(hora)}" if h else f'por volta das {hora}'


_DECIMAL = re.compile(r'(?<=\d)\.(?=\d)')
_HORA_DIGITAL = re.compile(r'\b(\d{1,2}):(\d{2})\b')


def decimal_br(texto: str) -> str:
    """'3.1 mm' -> '3,1 mm'. Na tela e na voz, o separador é a vírgula."""
    return _DECIMAL.sub(',', texto)


def para_voz(texto: str) -> str:
    """Última passada antes do Kokoro.

    O espeak por trás dele lê "3.1" como "três um" e "23:00" como "vinte e três
    zero zero". Vírgula decimal vira "vírgula"; hora digital que tenha escapado
    do roteiro vira extenso. Hora inválida (ex.: "25:99") fica como está.
    """
    def _hora(m):
        falada = _falada(m.group(0))
        return falada[1] if falada else m.group(0)
    return decimal_br(_HORA_DIGITAL.sub(_hora, texto))


def hora_agora() -> int:
    """Hora cheia em Brasilia. Isolada para os testes poderem fixar o relogio."""
    from ..collectors.base import now
    return now().hour

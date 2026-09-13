# -*- coding: utf-8 -*-
"""Interpreta o que chegou: comando, pedido de previsao ou relato de tempo.

O resolver geografico (secao 4.4) ja ignora ruido conversacional, entao aqui
so sobra o que ele nao faz: separar comando de texto livre e reconhecer a
condicao meteorologica que a pessoa relatou.
"""
from __future__ import annotations

import re
import unicodedata

CONDICOES = {
    "chuva": "chuva", "chovendo": "chuva", "chove": "chuva",
    "chuvinha": "garoa", "garoa": "garoa", "garoando": "garoa",
    "sol": "sol", "ensolarado": "sol", "solzao": "sol", "limpo": "sol",
    "nublado": "nublado", "nuvens": "nublado", "fechado": "nublado",
    "encoberto": "nublado", "vento": "vento", "ventando": "vento",
    "neblina": "neblina", "cerracao": "neblina", "granizo": "granizo",
    "abafado": "abafado", "calor": "abafado",
}
COMANDOS = {"radar", "ajuda", "hoje", "amanha"}
_RUIDO_RELATO = {"esta", "ta", "aqui", "agora", "sim", "nao", "muito",
                 "forte", "fraco", "pouco", "bastante", "em", "no", "na"}
_PREFIXO_PEDIDO = re.compile(
    r"^\s*(?:previs[aã]o|tempo|clima)(?:\s+(?:para|pra|de|do|da|em|no|na))?\s*[:\-]?\s*",
    re.IGNORECASE)
_MENCAO = re.compile(r"@previsaorj\b", re.IGNORECASE)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().strip().split())


def limpar_pedido(texto: str) -> str:
    """Tira a mencao ao perfil e o 'previsao de ...' que vem colado no pedido."""
    texto = _MENCAO.sub(" ", texto or "")
    return _PREFIXO_PEDIDO.sub("", texto).strip()


def comando(texto: str) -> tuple[str | None, str]:
    """Devolve (comando, argumento). Comando e sempre a primeira palavra."""
    partes = normalizar(texto).split(maxsplit=1)
    if partes and partes[0] in COMANDOS:
        return partes[0], partes[1] if len(partes) > 1 else ""
    return None, ""


def condicao_simples(texto: str) -> str | None:
    """So aceita mensagem que E uma condicao. 'chuva' sim; 'vai ter chuva?' nao.

    Isso protege o radar: uma pergunta sobre chuva nao pode virar relato de
    chuva, senao o resumo colaborativo passa a medir curiosidade, nao tempo.
    """
    normal = normalizar(texto)
    if normal in {"nao", "sem chuva", "nao esta chovendo", "nao ta chovendo",
                  "parou", "parou de chover"}:
        return "sem chuva"
    if "?" in (texto or ""):
        return None
    fichas = re.findall(r"[a-z0-9]+", normal)
    encontradas = [CONDICOES[f] for f in fichas if f in CONDICOES]
    sobra = [f for f in fichas if f not in CONDICOES and f not in _RUIDO_RELATO]
    if len(set(encontradas)) == 1 and not sobra:
        return encontradas[0]
    return None


def condicao_no_texto(texto: str) -> str | None:
    """Primeira condicao citada, para 'chuva forte no Meier'."""
    if "?" in (texto or ""):
        return None
    for ficha in re.findall(r"[a-z0-9]+", normalizar(texto)):
        if ficha in CONDICOES:
            return CONDICOES[ficha]
    return None


def sem_condicao(texto: str) -> str:
    """Texto sem as palavras de condicao, para sobrar so o local."""
    normal = normalizar(texto)
    for palavra in CONDICOES:
        normal = re.sub(rf"\b{re.escape(palavra)}\b", " ", normal)
    for palavra in _RUIDO_RELATO:
        normal = re.sub(rf"\b{re.escape(palavra)}\b", " ", normal)
    return " ".join(normal.split())

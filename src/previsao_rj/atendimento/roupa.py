# -*- coding: utf-8 -*-
"""Linha de decisao do dia: o que a previsao muda na vida de quem perguntou.

A promessa da marca e "o tempo do Rio para decidir seu dia" (config/brand.yml).
Numero sozinho nao decide nada; por isso toda resposta termina com uma frase
curta de decisao, e ela muda conforme o local: em bairro de praia entra a
leitura de praia, no resto entra a de deslocamento.
"""
from __future__ import annotations


def recomendar(tmin: float, tmax: float, prob_chuva: float,
               rajada_kmh: float = 0.0, uv: float = 0.0,
               praia: bool = False) -> str:
    pecas: list[str] = []
    if tmin <= 15:
        pecas.append("casaco")
    elif tmin <= 19:
        pecas.append("blusa leve")
    else:
        pecas.append("roupa leve")
    if prob_chuva >= 60:
        pecas.append("guarda-chuva")
    elif prob_chuva >= 35:
        pecas.append("guarda-chuva na mochila")
    if tmax >= 32:
        pecas.append("garrafa d'agua")
    if rajada_kmh >= 45:
        pecas.append("capa de chuva, que guarda-chuva vira do avesso")
    linha = "👕 O dia pede: " + " + ".join(pecas) + "."

    if praia:
        linha += "\n" + _leitura_praia(prob_chuva, rajada_kmh, uv, tmax)
    return linha


def _leitura_praia(prob_chuva: float, rajada_kmh: float, uv: float,
                   tmax: float) -> str:
    if prob_chuva >= 60:
        return "🏖️ Praia: dia ruim, chuva provavel."
    if rajada_kmh >= 40:
        return "🏖️ Praia: vento forte, guarda-sol nao para em pe."
    if prob_chuva >= 35:
        return "🏖️ Praia: janela curta, pode fechar o tempo."
    base = "🏖️ Praia: dia bom"
    if tmax < 25:
        base = "🏖️ Praia: ceu ajuda, mas o calor nao"
    if uv >= 11:
        return base + ", UV extremo — protetor e sombra depois das 10h."
    if uv >= 8:
        return base + ", UV muito alto — protetor a cada 2h."
    return base + "."

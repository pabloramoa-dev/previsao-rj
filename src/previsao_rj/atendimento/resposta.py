# -*- coding: utf-8 -*-
"""Monta o texto que a pessoa recebe.

Duas regras de conteudo, herdadas do plano:

1. A resposta traz HOJE e AMANHA. O Reel do perfil ja conta um dia; uma DM que
   repetisse o mesmo dia seria redundante com o video que a pessoa acabou de
   ver. Com dois dias ela sempre recebe algo que o video nao deu.

2. A resposta termina em decisao, nao em numero — "o tempo do Rio para decidir
   seu dia" (config/brand.yml). Por isso a linha de roupa e, em bairro de
   praia, a leitura de praia.

O fecho muda conforme a pessoa segue o perfil. Quem nao segue recebe a primeira
resposta por cortesia e um convite; a decisao de gastar essa cortesia e do
webhook, aqui so muda o texto. Quando a API nao responde se a pessoa segue
(None), tratamos como seguidora: nunca bloquear alguem por erro nosso.
"""
from __future__ import annotations

from typing import Any

from .. import config
from ..geo import resolver as geo
from . import dados
from .roupa import recomendar

MSG_SIGA = (
    "Opa! A previsao do teu bairro agora e so pra quem segue o perfil 😉\n"
    "E de graca: segue o @previsaorj e manda o nome do bairro de novo "
    "que eu respondo na hora. 🌦️")

MSG_AJUDA = (
    "Eu respondo o tempo do teu canto do Rio 🌦️\n"
    "• Manda o BAIRRO (ou a praia, ou o estadio) e eu digo hoje e amanha\n"
    "• Pode mandar por audio, eu escuto\n"
    "• BAIRRO + CHUVA/SOL/VENTO/NUBLADO entra no radar dos seguidores\n"
    "• RADAR + ZONA mostra o que estao vendo agora")

MSG_INDISPONIVEL = (
    "A previsao esta temporariamente indisponivel. "
    "Tenta de novo daqui a pouco 🙏")

_FECHO_SEGUIDOR = "Compartilha com quem vai sair de casa! 🌦️"
_FECHO_CORTESIA = (
    "🔔 Essa foi por conta da casa. Segue o @previsaorj pra receber a previsao "
    "do teu bairro sempre que pedir. 🌦️")

_EXEMPLOS = ("Copacabana", "Tijuca", "Madureira", "Icarai",
             "Duque de Caxias", "Barra da Tijuca")


def nome_zona(local: dict[str, Any]) -> str:
    zonas = config.load_places().get("zones") or {}
    return (zonas.get(local.get("zone")) or {}).get("name", local.get("zone") or "")


def nome_municipio(local: dict[str, Any]) -> str:
    municipios = config.load_places().get("municipalities") or {}
    chave = local.get("municipality")
    return (municipios.get(chave) or {}).get("name", chave or "")


def rotulo(local: dict[str, Any]) -> str:
    """'Icarai (Niteroi)' — o municipio evita confusao entre nomes repetidos."""
    return f"{local['name']} ({nome_municipio(local)})"


def _fonte(previsao: dict) -> str:
    if previsao.get("_fonte") == "met_no":
        return "Dados: MET Norway (CC BY 4.0)."
    return "Dados: Open-Meteo (ECMWF/ICON/GFS)."


def texto_previsao(local: dict[str, Any], previsao: dict, segue) -> str:
    praia = bool(local.get("beach"))
    decisao = recomendar(
        previsao["tmin"], previsao["tmax"], previsao["prob_chuva"],
        previsao.get("rajada_kmh", 0.0), previsao.get("uv", 0.0), praia)
    fecho = _FECHO_SEGUIDOR if segue is not False else _FECHO_CORTESIA
    aviso = ""
    if local.get("spatial_fit") == "baixo":
        aviso = ("\n⚠️ Microclima: ali o tempo muda mais que o modelo "
                 "consegue enxergar.")
    return (
        f"📍 {rotulo(local)} — {nome_zona(local)}\n"
        f"🌡️ Hoje: {previsao['tmin']:.0f}° / {previsao['tmax']:.0f}°  "
        f"☔ chuva {previsao['prob_chuva']:.0f}%\n"
        f"🌅 Amanha: {previsao.get('tmin_amanha', previsao['tmin']):.0f}° / "
        f"{previsao.get('tmax_amanha', previsao['tmax']):.0f}°  "
        f"☔ chuva {previsao.get('prob_chuva_amanha', previsao['prob_chuva']):.0f}%\n"
        f"{decisao}{aviso}\n\n"
        f"{_fonte(previsao)}\n{fecho}")


def montar(texto: str, segue=None) -> tuple[str, bool, dict[str, Any] | None]:
    """Devolve (resposta, deu_previsao, local).

    `deu_previsao` diz ao webhook se esta resposta entregou a previsao mesmo
    (True) ou foi pergunta de desambiguacao / "nao achei" (False) — e por ela
    que o webhook decide se a cortesia do nao seguidor foi gasta.
    """
    resolucao = geo.resolve(texto)

    if resolucao.status == "ambiguous":
        opcoes = " ou ".join(rotulo(c) for c in resolucao.candidates)
        if len(resolucao.candidates) == 1:
            pergunta = f"Voce quis dizer {opcoes}? Me confirma que eu respondo."
        else:
            pergunta = f"Tem mais de um por aqui 😅 Qual: {opcoes}?"
        return pergunta, False, None

    if resolucao.status != "resolved" or not resolucao.location:
        return ("Nao achei esse lugar no meu mapa 😅\n"
                "Manda o nome do bairro, da praia ou do municipio — "
                f"tipo {', '.join(_EXEMPLOS[:3])} ou {_EXEMPLOS[3]}.",
                False, None)

    local = resolucao.location
    previsao = dados.previsao_do_local(local)
    if not previsao:
        return MSG_INDISPONIVEL, False, local

    resposta = texto_previsao(local, previsao, segue)
    if resolucao.confidence == "aproximada":
        resposta = f"(Entendi {local['name']}, me corrige se errei 😉)\n\n{resposta}"
    return resposta, True, local


def convite_radar(local: dict[str, Any]) -> str:
    return (f"\n\nE como esta o tempo em {local['name']} agora? "
            "Responde so: CHUVA, GAROA, NUBLADO, SOL ou VENTO.")

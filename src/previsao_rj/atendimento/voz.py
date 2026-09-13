# -*- coding: utf-8 -*-
"""Mensagem de voz: baixa o audio da DM e transcreve.

Por que transcricao hospedada e nao um modelo no proprio servico: o plano free
onde este webhook roda tem 512 MB de RAM e CPU fracionada. Carregar Whisper ali
derruba o servico inteiro — inclusive as respostas de texto, que funcionam bem.
A transcricao sai por HTTP em cerca de um segundo e o audio nao fica guardado
em lugar nenhum: ele existe na memoria do processo o tempo da chamada.

Sem GROQ_API_KEY o modulo nao quebra: ele diz que nao ha transcricao e o
webhook responde pedindo o bairro por escrito.
"""
from __future__ import annotations

import os

import requests

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODELO = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3-turbo")
TIMEOUT_DOWNLOAD = 20
TIMEOUT_TRANSCRICAO = 45
# Audio de DM pedindo previsao tem segundos. Acima disso e engano ou abuso.
TAMANHO_MAX = 8 * 1024 * 1024

MSG_SEM_TRANSCRICAO = (
    "Recebi teu audio, mas nao consegui escutar direito agora 😅\n"
    "Me manda o nome do bairro por escrito que eu respondo na hora.")


def habilitada() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def url_do_audio(mensagem: dict) -> str | None:
    """Primeiro anexo de audio da mensagem, se houver."""
    for anexo in mensagem.get("attachments") or []:
        if anexo.get("type") in {"audio", "voice"}:
            url = (anexo.get("payload") or {}).get("url")
            if url:
                return url
    return None


def _baixar(url: str, token: str | None) -> bytes | None:
    cabecalhos = {}
    resposta = requests.get(url, timeout=TIMEOUT_DOWNLOAD, stream=True)
    if resposta.status_code in (401, 403) and token:
        cabecalhos["Authorization"] = f"Bearer {token}"
        resposta = requests.get(url, headers=cabecalhos,
                                timeout=TIMEOUT_DOWNLOAD, stream=True)
    if resposta.status_code >= 400:
        print(f"[voz] download recusado ({resposta.status_code})")
        return None

    pedacos = bytearray()
    for pedaco in resposta.iter_content(64 * 1024):
        pedacos.extend(pedaco)
        if len(pedacos) > TAMANHO_MAX:
            print("[voz] audio maior que o limite; descartado")
            return None
    return bytes(pedacos)


def transcrever(url: str, token: str | None = None) -> str | None:
    """Devolve o texto falado, ou None se nao der para transcrever."""
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        print("[voz] GROQ_API_KEY ausente; transcricao desligada")
        return None
    try:
        audio = _baixar(url, token)
    except requests.RequestException as exc:
        print(f"[voz] erro ao baixar audio: {exc}")
        return None
    if not audio:
        return None

    try:
        resposta = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {chave}"},
            files={"file": ("audio.mp4", audio, "audio/mp4")},
            data={"model": MODELO, "language": "pt",
                  "response_format": "json", "temperature": "0"},
            timeout=TIMEOUT_TRANSCRICAO,
        )
    except requests.RequestException as exc:
        print(f"[voz] erro na transcricao: {exc}")
        return None

    if resposta.status_code >= 400:
        print(f"[voz] transcricao recusada ({resposta.status_code}): "
              f"{resposta.text[:200]}")
        return None
    texto = (resposta.json().get("text") or "").strip()
    return texto or None

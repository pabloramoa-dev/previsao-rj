# -*- coding: utf-8 -*-
"""Webhook do atendimento do @previsaorj — comentario, DM e mensagem de voz.

Rota de publicacao: API do Instagram com login do Instagram (graph.instagram.com).

Tres caminhos entram por aqui:

  comentario no Reel  -> Private Reply na DM + confirmacao curta no comentario
  DM de texto         -> previsao, radar ou ajuda
  DM de audio         -> transcricao e dai o mesmo caminho do texto

O POST responde 200 na hora e processa em outra thread. A Meta reenvia o evento
se o 200 demorar, e reenvio vira resposta duplicada; a deduplicacao por mid e
por id de comentario existe para o caso de o reenvio acontecer mesmo assim.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import threading
import time

import requests
from flask import Flask, jsonify, request

from . import dados, radar, resposta, voz
from .interacao import (comando, condicao_no_texto, condicao_simples,
                        limpar_pedido, sem_condicao)
from ..geo import resolver as geo

app = Flask(__name__)

VERIFY = os.environ.get("IG_VERIFY_TOKEN", "")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
APP_SECRET = os.environ.get("META_APP_SECRET", "")
VERSAO = os.environ.get("META_GRAPH_VERSION", "v22.0")
PERFIL = os.environ.get("EXPECTED_IG_USERNAME", "previsaorj").casefold()

BASE = f"https://graph.instagram.com/{VERSAO}"
MENSAGENS = f"{BASE}/me/messages"
INICIO = time.time()

_cortesia_gasta: set[str] = set()
_follow_cache: dict[str, tuple[float, bool]] = {}
_FOLLOW_TTL = 10 * 60
_assinado = False
_trava_assinatura = threading.Lock()
_trava_diag = threading.Lock()
_diag = {
    "webhooks": 0,
    "comentarios": 0,
    "dm_texto": 0,
    "dm_audio": 0,
    "audios_transcritos": 0,
    "previsoes_entregues": 0,
    "relatos_no_radar": 0,
    "respostas_publicas": 0,
    "ultimo_estagio": "aguardando_evento",
    "ultimo_http_meta": None,
}

_CONFIRMACOES = (
    "📩 Prontinho! A previsao ja esta na tua DM. 🌦️",
    "🌤️ Acabei de mandar a previsao na DM. Confere la!",
    "📍 A previsao do teu bairro chegou na DM.",
    "☔ Mensagem enviada! Ve a previsao completa na DM.",
    "✅ Tudo certo: hoje e amanha estao na tua DM.",
)


def _marcar(estagio: str, **valores) -> None:
    with _trava_diag:
        _diag["ultimo_estagio"] = estagio
        for chave, valor in valores.items():
            _diag[chave] = valor


def _contar(chave: str, estagio: str | None = None) -> None:
    with _trava_diag:
        _diag[chave] = _diag.get(chave, 0) + 1
        if estagio:
            _diag["ultimo_estagio"] = estagio


# ---------------------------------------------------------------- saude


@app.get("/ping")
def ping():
    _assinar()
    return jsonify({
        "status": "ok",
        "perfil": PERFIL,
        "uptime_s": int(time.time() - INICIO),
        "assinatura_meta": bool(APP_SECRET),
        "eventos_assinados": "ok" if _assinado else "pendente",
        "voz": "ok" if voz.habilitada() else "desligada",
        "radar": radar.estado(),
        "dados": dados.estado(),
    }), 200


@app.get("/diagnostico")
def diagnostico():
    """Telemetria sem texto de mensagem, sem ID de usuario e sem credencial."""
    with _trava_diag:
        estado = dict(_diag)
    estado["eventos_assinados"] = _assinado
    return jsonify(estado), 200


# ------------------------------------------------------------- webhook


@app.get("/webhook")
def verificar():
    if VERIFY and request.args.get("hub.verify_token") == VERIFY:
        return request.args.get("hub.challenge", ""), 200
    return "token invalido", 403


def _assinatura_valida(corpo: bytes) -> bool:
    if not APP_SECRET:
        return True
    recebida = request.headers.get("X-Hub-Signature-256", "")
    esperada = "sha256=" + hmac.new(
        APP_SECRET.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(recebida, esperada)


def _assinar() -> None:
    """Pede a Meta que mande comentarios e mensagens para este webhook."""
    global _assinado
    if _assinado or not TOKEN:
        return
    with _trava_assinatura:
        if _assinado:
            return
        try:
            r = requests.post(
                f"{BASE}/me/subscribed_apps",
                params={"subscribed_fields": "comments,messages",
                        "access_token": TOKEN},
                timeout=15)
            if r.status_code >= 400:
                print(f"[webhook] assinatura recusada ({r.status_code}): "
                      f"{r.text[:300]}")
                return
            _assinado = bool(r.json().get("success", True))
            print("[webhook] comentarios e mensagens assinados na Meta")
        except requests.RequestException as exc:
            print(f"[webhook] erro ao assinar eventos: {exc}")


@app.post("/webhook")
def receber():
    bruto = request.get_data(cache=True)
    if not _assinatura_valida(bruto):
        return "assinatura invalida", 403
    corpo = request.get_json(silent=True) or {}
    _contar("webhooks", "webhook_recebido")
    _assinar()
    threading.Thread(target=_processar, args=(corpo,), daemon=True).start()
    return "ok", 200


def _processar(corpo: dict) -> None:
    for entrada in corpo.get("entry", []) or []:
        id_perfil = str(entrada.get("id", ""))
        for valor in _comentarios(entrada):
            try:
                _tratar_comentario(valor, id_perfil)
            except Exception as exc:
                print(f"[webhook] falha no comentario: {exc}")
        for evento in entrada.get("messaging", []) or []:
            try:
                _tratar_dm(evento)
            except Exception as exc:
                print(f"[webhook] falha na DM: {exc}")


# --------------------------------------------------------------- DM


def _tratar_dm(evento: dict) -> None:
    mensagem = evento.get("message") or {}
    if mensagem.get("is_echo"):
        return
    destino = (evento.get("sender") or {}).get("id")
    if not destino:
        return

    texto = (mensagem.get("text") or "").strip()
    mid = mensagem.get("mid") or f"{destino}:{evento.get('timestamp')}"
    audio = voz.url_do_audio(mensagem)

    if not texto and audio:
        _contar("dm_audio", "audio_recebido")
        if not radar.marcar_evento(f"dm:{mid}"):
            return
        texto = voz.transcrever(audio, TOKEN) or ""
        if not texto:
            _enviar(destino, voz.MSG_SEM_TRANSCRICAO)
            return
        _contar("audios_transcritos", "audio_transcrito")
        print(f"[webhook] audio transcrito ({len(texto)} caracteres)")
    elif texto:
        _contar("dm_texto", "dm_recebida")
        if not radar.marcar_evento(f"dm:{mid}"):
            return
    else:
        return

    texto = limpar_pedido(texto)
    if not texto:
        _enviar(destino, resposta.MSG_AJUDA)
        return

    cmd, argumento = comando(texto)
    if cmd == "ajuda":
        _enviar(destino, resposta.MSG_AJUDA)
        return
    if cmd == "radar":
        _enviar(destino, _resumo_radar(argumento))
        return

    if _tentar_relato(destino, mid, texto):
        return

    _responder_previsao(destino, texto)


def _resumo_radar(argumento: str) -> str:
    if not argumento.strip():
        return radar.resumo()
    resolucao = geo.resolve(argumento)
    if resolucao.resolved and resolucao.location:
        return radar.resumo(resposta.nome_zona(resolucao.location))
    return radar.resumo()


def _tentar_relato(destino: str, mid: str, texto: str) -> bool:
    """Relato de tempo: resposta curta no contexto, ou 'chuva no Meier'."""
    curta = condicao_simples(texto)
    if curta:
        contexto = radar.obter_contexto(destino)
        if not contexto:
            return False
        zona, local_id, nome = contexto
        if radar.registrar(mid, destino, zona, nome, curta):
            _contar("relatos_no_radar", "relato_registrado")
            _enviar(destino, f"✅ Anotado: {curta} em {nome}. Valeu!\n"
                             + radar.resumo(zona))
        return True

    condicao = condicao_no_texto(texto)
    if not condicao:
        return False
    restante = sem_condicao(texto)
    if not restante:
        return False
    resolucao = geo.resolve(restante)
    if not (resolucao.resolved and resolucao.location):
        return False
    local = resolucao.location
    zona = resposta.nome_zona(local)
    if radar.registrar(mid, destino, zona, local["name"], condicao):
        _contar("relatos_no_radar", "relato_registrado")
        _enviar(destino, f"✅ Relato recebido: {condicao} em {local['name']}. "
                         "Obrigado!\n" + radar.resumo(zona))
    return True


def _responder_previsao(destino: str, texto: str) -> None:
    segue = _segue(destino)
    if segue is False and destino in _cortesia_gasta:
        _enviar(destino, resposta.MSG_SIGA)
        return

    texto_resposta, deu_previsao, local = resposta.montar(texto, segue)
    if deu_previsao and local:
        radar.guardar_contexto(destino, resposta.nome_zona(local),
                               local["id"], local["name"])
        texto_resposta += resposta.convite_radar(local)
        _contar("previsoes_entregues", "previsao_entregue")
    _enviar(destino, texto_resposta)
    if segue is False and deu_previsao:
        _cortesia_gasta.add(destino)


def _segue(uid: str):
    """True/False, ou None quando a API nao responde — ai tratamos como segue."""
    if not TOKEN:
        return None
    agora = time.time()
    em_cache = _follow_cache.get(uid)
    if em_cache and agora - em_cache[0] < _FOLLOW_TTL:
        return em_cache[1]
    try:
        r = requests.get(f"{BASE}/{uid}",
                         params={"fields": "is_user_follow_business",
                                 "access_token": TOKEN},
                         timeout=10)
        if r.status_code >= 400:
            print(f"[webhook] perfil indisponivel ({r.status_code})")
            return None
        segue = bool(r.json().get("is_user_follow_business"))
        _follow_cache[uid] = (agora, segue)
        return segue
    except requests.RequestException as exc:
        print(f"[webhook] erro ao checar follow: {exc}")
        return None


# --------------------------------------------------------- comentarios


def _comentarios(entrada: dict):
    """A Meta manda comentario em dois formatos; aceitamos os dois."""
    if entrada.get("field") in {"comments", "live_comments"}:
        valor = entrada.get("value")
        if isinstance(valor, dict):
            yield valor
    for alteracao in entrada.get("changes", []) or []:
        if alteracao.get("field") not in {"comments", "live_comments"}:
            continue
        valor = alteracao.get("value")
        if isinstance(valor, dict):
            yield valor


def _tratar_comentario(valor: dict, id_perfil: str) -> None:
    comentario_id = str(valor.get("id") or "")
    _contar("comentarios", "comentario_recebido")
    texto = limpar_pedido(str(valor.get("text") or ""))
    autor = valor.get("from") or {}
    autor_id = str(autor.get("id") or "")
    usuario = str(autor.get("username") or "").casefold()
    if (not comentario_id or not texto
            or (autor_id and autor_id == id_perfil) or usuario == PERFIL):
        return

    resolucao = geo.resolve(texto)
    if resolucao.status == "unknown":
        _marcar("comentario_sem_local")
        return
    if not radar.marcar_evento(f"comentario:{comentario_id}"):
        _marcar("comentario_duplicado")
        return

    texto_resposta, deu_previsao, _ = resposta.montar(texto, True)
    if deu_previsao:
        _contar("previsoes_entregues", "previsao_entregue")
    if _private_reply(comentario_id, texto_resposta):
        _responder_comentario(comentario_id, _confirmacao(comentario_id))


def _confirmacao(comentario_id: str) -> str:
    """Distribui as frases sem guardar estado e sem mudar no reprocessamento."""
    indice = hashlib.sha256(comentario_id.encode()).digest()[0]
    return _CONFIRMACOES[indice % len(_CONFIRMACOES)]


def _private_reply(comentario_id: str, texto: str) -> bool:
    try:
        r = requests.post(
            MENSAGENS,
            params={"access_token": TOKEN},
            json={"recipient": {"comment_id": comentario_id},
                  "message": {"text": texto[:1000]}},
            timeout=15)
        if r.status_code >= 400:
            _marcar("dm_recusada", ultimo_http_meta=r.status_code)
            print(f"[webhook] private reply recusada ({r.status_code}): "
                  f"{r.text[:300]}")
            return False
        _marcar("dm_enviada", ultimo_http_meta=r.status_code)
        return True
    except requests.RequestException as exc:
        print(f"[webhook] erro na private reply: {exc}")
        return False


def _responder_comentario(comentario_id: str, texto: str) -> bool:
    try:
        r = requests.post(f"{BASE}/{comentario_id}/replies",
                          params={"access_token": TOKEN},
                          data={"message": texto[:2200]},
                          timeout=15)
        if r.status_code >= 400:
            _marcar("resposta_publica_recusada", ultimo_http_meta=r.status_code)
            print(f"[webhook] resposta ao comentario recusada "
                  f"({r.status_code}): {r.text[:300]}")
            return False
        _contar("respostas_publicas", "fluxo_concluido")
        return True
    except requests.RequestException as exc:
        print(f"[webhook] erro ao responder comentario: {exc}")
        return False


def _enviar(uid: str, texto: str) -> None:
    if not TOKEN:
        print("[webhook] sem IG_ACCESS_TOKEN; resposta nao enviada")
        return
    try:
        r = requests.post(MENSAGENS,
                          params={"access_token": TOKEN},
                          json={"recipient": {"id": uid},
                                "message": {"text": texto[:1000]}},
                          timeout=15)
        if r.status_code >= 400:
            print(f"[webhook] Instagram recusou ({r.status_code}): "
                  f"{r.text[:300]}")
    except requests.RequestException as exc:
        print(f"[webhook] erro ao responder: {exc}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

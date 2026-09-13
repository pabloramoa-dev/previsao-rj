# -*- coding: utf-8 -*-
"""Testes do webhook: o que sai pela Meta em cada evento que entra.

O envio e interceptado, entao nada vai para a rede. Como o webhook responde 200
e processa em outra thread, os testes chamam o processamento direto — e o que
importa aqui e a decisao, nao o modelo de concorrencia do Flask.
"""
from __future__ import annotations

import pytest

from src.previsao_rj.atendimento import app as webhook
from src.previsao_rj.atendimento import dados, radar

PREVISAO = {
    "tmin": 20.0, "tmax": 31.0, "prob_chuva": 30.0, "rajada_kmh": 15.0,
    "uv": 9.0, "tmin_amanha": 21.0, "tmax_amanha": 30.0,
    "prob_chuva_amanha": 60.0, "rajada_kmh_amanha": 20.0, "uv_amanha": 8.0,
    "_fonte": "open_meteo",
}


@pytest.fixture
def enviadas(monkeypatch):
    saida: list[tuple[str, str]] = []
    monkeypatch.setattr(dados, "previsao_do_local", lambda local: dict(PREVISAO))
    monkeypatch.setattr(webhook, "_enviar",
                        lambda uid, texto: saida.append((uid, texto)))
    monkeypatch.setattr(webhook, "_segue", lambda uid: True)
    radar._MEMORIA.clear()
    radar._EVENTOS.clear()
    radar._EVENTOS_SET.clear()
    radar._CONTEXTOS.clear()
    webhook._cortesia_gasta.clear()
    return saida


def dm(texto=None, mid="m1", uid="u1", audio=None):
    mensagem = {"mid": mid}
    if texto is not None:
        mensagem["text"] = texto
    if audio:
        mensagem["attachments"] = [{"type": "audio", "payload": {"url": audio}}]
    return {"sender": {"id": uid}, "timestamp": 1, "message": mensagem}


def test_dm_de_texto_responde_previsao_e_convida_para_o_radar(enviadas):
    webhook._tratar_dm(dm("botafogo"))
    assert len(enviadas) == 1
    uid, texto = enviadas[0]
    assert uid == "u1"
    assert "Botafogo" in texto and "Zona Sul" in texto
    assert "CHUVA, GAROA" in texto


def test_mesma_mensagem_reenviada_nao_responde_duas_vezes(enviadas):
    webhook._tratar_dm(dm("botafogo", mid="m7"))
    webhook._tratar_dm(dm("botafogo", mid="m7"))
    assert len(enviadas) == 1


def test_eco_do_proprio_perfil_e_ignorado(enviadas):
    evento = dm("copacabana")
    evento["message"]["is_echo"] = True
    webhook._tratar_dm(evento)
    assert enviadas == []


def test_resposta_curta_depois_da_previsao_vira_relato(enviadas):
    webhook._tratar_dm(dm("meier", mid="m1"))
    webhook._tratar_dm(dm("chuva", mid="m2"))
    assert "Anotado: chuva em M" in enviadas[-1][1]
    assert "Radar dos seguidores" in enviadas[-1][1]


def test_condicao_sem_contexto_cai_na_previsao_e_nao_no_radar(enviadas):
    webhook._tratar_dm(dm("chuva", mid="m3"))
    assert "Nao achei" in enviadas[-1][1]
    assert radar.estado()["relatos_em_memoria"] == 0


def test_comando_radar_por_zona(enviadas):
    radar.registrar("r1", "u2", "Zona Norte", "Meier", "chuva")
    webhook._tratar_dm(dm("radar meier", mid="m4"))
    assert "Zona Norte" in enviadas[-1][1]


def test_ajuda_explica_audio(enviadas):
    webhook._tratar_dm(dm("ajuda", mid="m5"))
    assert "audio" in enviadas[-1][1]


def test_audio_transcrito_segue_o_caminho_do_texto(enviadas, monkeypatch):
    monkeypatch.setattr(webhook.voz, "transcrever",
                        lambda url, token=None: "como ta o tempo em icarai")
    webhook._tratar_dm(dm(audio="https://x/y.mp4", mid="a1"))
    assert "Icara" in enviadas[-1][1]
    assert "Niter" in enviadas[-1][1]


def test_audio_sem_transcricao_pede_texto(enviadas, monkeypatch):
    monkeypatch.setattr(webhook.voz, "transcrever", lambda url, token=None: None)
    webhook._tratar_dm(dm(audio="https://x/y.mp4", mid="a2"))
    assert "por escrito" in enviadas[-1][1]


def test_nao_seguidor_recebe_cortesia_uma_vez_so(enviadas, monkeypatch):
    monkeypatch.setattr(webhook, "_segue", lambda uid: False)
    webhook._tratar_dm(dm("bangu", mid="c1"))
    assert "por conta da casa" in enviadas[-1][1]
    webhook._tratar_dm(dm("bangu", mid="c2"))
    assert "segue o @previsaorj" in enviadas[-1][1]
    assert "Hoje:" not in enviadas[-1][1]


def test_comentario_manda_dm_e_confirma_em_publico(monkeypatch):
    privadas: list[tuple[str, str]] = []
    publicas: list[tuple[str, str]] = []
    monkeypatch.setattr(dados, "previsao_do_local", lambda local: dict(PREVISAO))
    monkeypatch.setattr(webhook, "_private_reply",
                        lambda cid, texto: privadas.append((cid, texto)) or True)
    monkeypatch.setattr(webhook, "_responder_comentario",
                        lambda cid, texto: publicas.append((cid, texto)) or True)
    radar._EVENTOS.clear()
    radar._EVENTOS_SET.clear()

    valor = {"id": "cmt1", "text": "previsao pra Madureira?",
             "from": {"id": "u5", "username": "alguem"}}
    webhook._tratar_comentario(valor, "perfil")
    webhook._tratar_comentario(valor, "perfil")   # reenvio da Meta

    assert len(privadas) == 1 and len(publicas) == 1
    assert "Madureira" in privadas[0][1]
    assert "DM" in publicas[0][1]


def test_comentario_do_proprio_perfil_nao_gera_resposta(monkeypatch):
    chamou = []
    monkeypatch.setattr(webhook, "_private_reply",
                        lambda cid, texto: chamou.append(cid) or True)
    webhook._tratar_comentario(
        {"id": "cmt2", "text": "copacabana",
         "from": {"id": "perfil", "username": "previsaorj"}}, "perfil")
    assert chamou == []


def test_comentario_sem_local_nao_vira_dm(monkeypatch):
    chamou = []
    monkeypatch.setattr(webhook, "_private_reply",
                        lambda cid, texto: chamou.append(cid) or True)
    webhook._tratar_comentario(
        {"id": "cmt3", "text": "que video bom!",
         "from": {"id": "u6", "username": "alguem"}}, "perfil")
    assert chamou == []


def test_verificacao_do_webhook(monkeypatch):
    monkeypatch.setattr(webhook, "VERIFY", "segredo")
    cliente = webhook.app.test_client()
    ok = cliente.get("/webhook?hub.verify_token=segredo&hub.challenge=123")
    assert ok.status_code == 200 and ok.data == b"123"
    negado = cliente.get("/webhook?hub.verify_token=errado&hub.challenge=123")
    assert negado.status_code == 403


def test_assinatura_invalida_e_recusada(monkeypatch):
    monkeypatch.setattr(webhook, "APP_SECRET", "segredo")
    cliente = webhook.app.test_client()
    r = cliente.post("/webhook", json={"entry": []},
                     headers={"X-Hub-Signature-256": "sha256=errado"})
    assert r.status_code == 403


def test_diagnostico_nao_expoe_credencial_nem_texto(monkeypatch):
    monkeypatch.setattr(webhook, "TOKEN", "token-secreto")
    corpo = webhook.app.test_client().get("/diagnostico").get_json()
    assert "token-secreto" not in str(corpo)
    assert set(corpo) >= {"webhooks", "comentarios", "dm_audio"}

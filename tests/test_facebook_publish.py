"""Publicador do Facebook com uma Meta falsa — nenhuma chamada sai da máquina."""
from __future__ import annotations

import json

import pytest

from src.previsao_rj.publish import facebook as fb


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class FakeMeta:
    """Simula a Graph API: start/upload/status/finish/confirm."""

    def __init__(self, page_id="111", name="Previsão RJ", fail=None):
        self.page_id, self.name, self.fail = page_id, name, dict(fail or {})
        self.calls = []
        self.finished = set()

    def request(self, method, url, timeout=None, params=None, data=None, headers=None):
        self.calls.append((method, url, dict(data or params or {}), dict(headers or {})))
        tag = url.rsplit("/", 1)[-1]
        if tag in self.fail and self.fail[tag]:
            status, body = self.fail[tag].pop(0)
            return FakeResp(status, body)
        if "rupload" in url:
            return FakeResp(200, {"success": True})
        if method == "GET" and tag == "me":
            return FakeResp(200, {"id": self.page_id, "name": self.name})
        if method == "GET" and tag == self.page_id:
            return FakeResp(200, {"id": self.page_id, "name": self.name, "username": "previsaorj"})
        if method == "POST" and tag in {"video_reels", "video_stories"}:
            if (data or {}).get("upload_phase") == "start":
                return FakeResp(200, {"video_id": "v1", "upload_url": "x"})
            self.finished.add(data["video_id"])
            return FakeResp(200, {"success": True, "post_id": "p1"})
        if method == "GET" and tag == "v1":
            done = "v1" in self.finished
            return FakeResp(200, {"status": {
                "video_status": "ready", "uploading_phase": {"status": "complete"},
                "processing_phase": {"status": "complete"},
                "publishing_phase": {"status": "complete" if done else "not_started"}},
                "permalink_url": "/reel/v1" if done else None})
        return FakeResp(404, {"error": {"code": 100, "message": "?"}})


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("FACEBOOK_PUBLISH_ENABLED", "true")
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "111")
    monkeypatch.setenv("FACEBOOK_PAGE_ACCESS_TOKEN", "EAA" + "x" * 30)
    monkeypatch.setenv("FACEBOOK_EXPECTED_PAGE", "Previsão RJ")
    monkeypatch.setattr(fb.time, "sleep", lambda s: None)
    return tmp_path / "fb.json"


def client(meta):
    return fb.Client(fb.Config(), session=meta)


def test_desligado_por_padrao(monkeypatch, tmp_path):
    monkeypatch.delenv("FACEBOOK_PUBLISH_ENABLED", raising=False)
    assert fb.run("reel", "u", "c", "k", repo="r", state_path=tmp_path / "s.json")["status"] == "disabled"


def test_publica_uma_vez_e_reaproveita_url(env):
    meta = FakeMeta()
    e = fb.run("reel", "https://github.com/x/releases/download/t/REEL.mp4", "Previsão #rio",
               "k1", repo="r", state_path=env, client=client(meta), confirm_every=0)
    assert e["status"] == "published" and e["video_id"] == "v1"
    up = [c for c in meta.calls if "rupload" in c[1]][0]
    assert up[3]["file_url"].endswith("REEL.mp4")          # mesmo MP4, sem reenvio
    n = len(meta.calls)
    again = fb.run("reel", "u", "Previsão", "k1", repo="r", state_path=env, client=client(meta))
    assert again["status"] == "published" and len(meta.calls) == n  # nada repetido


def test_token_e_destino_errados_bloqueiam(env):
    with pytest.raises(fb.FacebookError) as exc:
        fb.run("reel", "u", "c", "k", repo="r", state_path=env,
               client=client(FakeMeta(name="Outra Página")))
    assert exc.value.kind == "destination"


def test_oauth_190_nao_repete(env):
    meta = FakeMeta(fail={"me": [(400, {"error": {"code": 190, "message": "expired"}})] * 5})
    with pytest.raises(fb.FacebookError) as exc:
        fb.run("reel", "u", "c", "k", repo="r", state_path=env, client=client(meta))
    assert exc.value.kind == "auth" and len(meta.calls) == 1


def test_instabilidade_tenta_de_novo(env):
    meta = FakeMeta(fail={"me": [(500, {"error": {"code": 2, "message": "tmp"}})]})
    e = fb.run("reel", "u", "c", "k", repo="r", state_path=env, client=client(meta), confirm_every=0)
    assert e["status"] == "published"


def test_falha_registra_e_permite_reenviar_so_o_facebook(env):
    meta = FakeMeta(fail={"video_reels": [(400, {"error": {"code": 368, "message": "x"}})]})
    with pytest.raises(fb.FacebookError):
        fb.run("reel", "u", "c", "k", repo="r", state_path=env, client=client(meta))
    st = json.loads(env.read_text())
    assert list(st.values())[0]["status"] == "failed"
    e = fb.run("reel", "u", "c", "k", repo="r", state_path=env, client=client(meta), confirm_every=0)
    assert e["status"] == "published" and e["attempts"] == 2


def test_redacao_de_token():
    assert "EAA***" in fb._redact("token EAA" + "a" * 40)
    assert "access_token=***" in fb._redact("?access_token=abc&x=1")


def test_legenda_facebook():
    ig = "Previsão para Niterói 28°C\nLink na bio!\n#rio #tempo #chuva #rj #clima"
    out = fb.facebook_caption(ig, "k")
    assert "Link na bio" not in out and "Niterói 28°C" in out
    assert len([t for t in out.split() if t.startswith("#")]) == 3
    assert out.splitlines()[-1] in fb.CTAS
    assert fb.facebook_caption(ig, "k") == out
    serra = fb.facebook_caption("Interdição na Serra das Araras", "k")
    assert serra.endswith(fb.CTA_SERRA)

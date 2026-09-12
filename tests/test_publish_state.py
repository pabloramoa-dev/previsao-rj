"""Estado persistente do publicador: reivindicar, confirmar, soltar e travar.

O que estes testes protegem (secoes 13.4 e 18): nada e publicado duas vezes,
nada volta para a fila depois que a Meta pode ter aceitado, e o historico que
o motor editorial le sai realmente do que foi publicado.
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest

from src.previsao_rj.collectors.base import iso, now
from src.previsao_rj.editorial import engine
from src.previsao_rj.publish import state


def _item(dedupe_key="k1", *, status="ready", total=20, expires_in_hours=2, **extra):
    base = {
        "dedupe_key": dedupe_key,
        "hook_key": "hook-" + dedupe_key,
        "format": "rio_antes_de_sair",
        "topic": "resumo",
        "character": "bira",
        "classification": "reel",
        "facts": {"copacabana": {"max_c": 30}},
        "total": total,
        "status": status,
        "expires_at": iso(now() + timedelta(hours=expires_in_hours)),
    }
    base.update(extra)
    return base


@pytest.fixture
def queue(tmp_path):
    path = tmp_path / "fila.json"
    state.save(path, [_item()])
    return path


def test_claim_marca_publishing_e_carimba_hora(queue):
    claimed = state.claim(queue, "k1")
    assert claimed["status"] == "publishing"
    assert claimed["claimed_at"]
    assert state.load(queue)[0]["status"] == "publishing"


def test_claim_duas_vezes_e_recusado(queue):
    state.claim(queue, "k1")
    with pytest.raises(state.QueueError, match="reivindicado"):
        state.claim(queue, "k1")


def test_item_publicado_nunca_e_reivindicado_de_novo(queue):
    state.claim(queue, "k1")
    state.commit(queue, "k1", media_id="17900000000000000")
    with pytest.raises(state.QueueError, match="ja publicado"):
        state.claim(queue, "k1")


def test_commit_grava_media_id_e_published_at(queue):
    state.claim(queue, "k1")
    committed = state.commit(queue, "k1", media_id="17900000000000000")
    assert committed["status"] == "published"
    assert committed["media_id"] == "17900000000000000"
    assert committed["published_at"]


def test_release_devolve_para_ready_com_motivo(queue):
    state.claim(queue, "k1")
    released = state.release(queue, "k1", "timeout no container")
    assert released["status"] == "ready"
    assert released["release_reason"] == "timeout no container"
    assert "claimed_at" not in released
    # e pode ser reivindicado de novo, porque nada foi ao ar
    assert state.claim(queue, "k1")["status"] == "publishing"


def test_unknown_trava_o_item_para_conferencia_humana(queue):
    state.claim(queue, "k1")
    state.mark_unknown(queue, "k1", "falha durante media_publish")
    with pytest.raises(state.QueueError, match="conferencia humana"):
        state.claim(queue, "k1")


def test_item_vencido_nao_e_publicado_e_vira_expired(tmp_path):
    path = tmp_path / "fila.json"
    state.save(path, [_item("velho", expires_in_hours=-1)])
    with pytest.raises(state.QueueError, match="vencida"):
        state.claim(path, "velho")
    assert state.load(path)[0]["status"] == "expired"


def test_next_ready_escolhe_maior_total_e_ignora_vencido(tmp_path):
    path = tmp_path / "fila.json"
    state.save(path, [
        _item("baixo", total=10),
        _item("alto", total=25),
        _item("vencido", total=99, expires_in_hours=-1),
        _item("bloqueado", total=99, status="blocked"),
    ])
    assert state.next_ready(path)["dedupe_key"] == "alto"


def test_next_ready_vazio_quando_nada_esta_pronto(tmp_path):
    path = tmp_path / "fila.json"
    state.save(path, [_item("b", status="blocked")])
    assert state.next_ready(path) is None


def test_history_devolve_so_publicados_em_ordem(tmp_path):
    path = tmp_path / "fila.json"
    state.save(path, [_item("a"), _item("b"), _item("c", status="blocked")])
    for key in ("a", "b"):
        state.claim(path, key)
        state.commit(path, key, media_id="id-" + key)
    hist = state.history(path)
    assert [h["dedupe_key"] for h in hist] == ["a", "b"]
    assert all(h["status"] == "published" for h in hist)


def test_fila_sobrevive_a_escrita_atomica(queue):
    state.claim(queue, "k1")
    conteudo = json.loads(queue.read_text(encoding="utf-8"))
    assert isinstance(conteudo, list) and conteudo[0]["status"] == "publishing"
    assert not queue.with_suffix(".tmp").exists()


def test_item_ausente_da_erro_claro(queue):
    with pytest.raises(state.QueueError, match="ausente"):
        state.claim(queue, "nao-existe")


def test_historico_do_publicador_arma_o_veto_de_duplicata(snapshot, tmp_path):
    """O ciclo completo: publicar alimenta o historico que veta a repeticao."""
    fila = tmp_path / "fila.json"
    primeiro = engine.evaluate(snapshot)
    pronto = next(c for c in primeiro if c["status"] == "ready")
    engine.queue_file(fila, primeiro)

    state.claim(fila, pronto["dedupe_key"])
    state.commit(fila, pronto["dedupe_key"], media_id="17900000000000000")

    segundo = engine.evaluate(snapshot, history=state.history(fila))
    repetido = next(c for c in segundo if c["dedupe_key"] == pronto["dedupe_key"])
    assert "duplicata" in repetido["vetoes"]
    assert repetido["status"] == "blocked"


def test_queue_file_nao_sobrescreve_item_publicado(snapshot, tmp_path):
    fila = tmp_path / "fila.json"
    avaliados = engine.evaluate(snapshot)
    engine.queue_file(fila, avaliados)
    pronto = next(c for c in avaliados if c["status"] == "ready")

    state.claim(fila, pronto["dedupe_key"])
    state.commit(fila, pronto["dedupe_key"], media_id="17900000000000000")

    engine.queue_file(fila, engine.evaluate(snapshot))
    guardado = state.find(state.load(fila), pronto["dedupe_key"])
    assert guardado["status"] == "published"
    assert guardado["media_id"] == "17900000000000000"


# ---------------------------------------------------------------------------
# CLI: o modelo de risco (o que volta para a fila e o que trava) mora aqui.
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    from src.previsao_rj.publish import cli

    legenda = tmp_path / "LEGENDA.txt"
    legenda.write_text("Previsao de hoje no @previsaorj", encoding="utf-8")
    fila = tmp_path / "fila.json"
    state.save(fila, [_item("k1", total=25)])

    monkeypatch.setattr(cli, "verify_destination", lambda: {"username": "previsaorj"})
    monkeypatch.setattr(cli, "already_published_caption", lambda caption: False)
    monkeypatch.setattr(cli, "create_reel", lambda url, caption: "container-1")
    monkeypatch.setattr(cli, "wait_ready", lambda container: None)
    monkeypatch.setattr(cli, "publish", lambda container: "17900000000000000")

    def run(*extra):
        monkeypatch.setattr("sys.argv", [
            "cli", "--video-url", "https://exemplo/REEL.mp4",
            "--caption-file", str(legenda), "--queue", str(fila), *extra])
        cli.main()

    return cli, run, fila


def test_cli_dry_run_nao_toca_na_fila(cli_env):
    _, run, fila = cli_env
    run()
    assert state.load(fila)[0]["status"] == "ready"


def test_cli_publica_e_marca_published(cli_env):
    _, run, fila = cli_env
    run("--publish")
    item = state.load(fila)[0]
    assert item["status"] == "published"
    assert item["media_id"] == "17900000000000000"


def test_cli_nao_republica_o_mesmo_item_no_modo_automatico(cli_env):
    """Publicado sai de `ready`: a segunda execucao nem encontra o que publicar."""
    _, run, fila = cli_env
    run("--publish")
    with pytest.raises(SystemExit, match="nada a publicar"):
        run("--publish")


def test_cli_recusa_republicar_item_apontado_a_dedo(cli_env):
    """Mesmo forcando o dedupe_key, a fila barra o item ja publicado."""
    _, run, fila = cli_env
    run("--publish")
    key = state.load(fila)[0]["dedupe_key"]
    with pytest.raises(state.QueueError, match="ja publicado"):
        run("--publish", "--dedupe-key", key)


def test_cli_falha_antes_da_midia_devolve_para_ready(cli_env, monkeypatch):
    cli, run, fila = cli_env
    monkeypatch.setattr(cli, "wait_ready",
                        lambda container: (_ for _ in ()).throw(TimeoutError("container travou")))
    with pytest.raises(TimeoutError):
        run("--publish")
    item = state.load(fila)[0]
    assert item["status"] == "ready"
    assert "falha antes de publicar" in item["release_reason"]


def test_cli_falha_durante_media_publish_trava_em_unknown(cli_env, monkeypatch):
    cli, run, fila = cli_env
    monkeypatch.setattr(cli, "publish",
                        lambda container: (_ for _ in ()).throw(RuntimeError("502 da Meta")))
    with pytest.raises(RuntimeError):
        run("--publish")
    item = state.load(fila)[0]
    assert item["status"] == "unknown"
    assert "media_publish" in item["release_reason"]


def test_cli_recusa_legenda_sem_a_marca(cli_env, tmp_path, monkeypatch):
    cli, _, fila = cli_env
    sem_marca = tmp_path / "SEM.txt"
    sem_marca.write_text("previsao de hoje", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["cli", "--video-url", "https://exemplo/REEL.mp4",
                                     "--caption-file", str(sem_marca), "--queue", str(fila),
                                     "--publish"])
    with pytest.raises(SystemExit, match="@previsaorj"):
        cli.main()
    assert state.load(fila)[0]["status"] == "ready"


def test_cli_sem_item_pronto_nao_publica(cli_env, tmp_path):
    cli, run, fila = cli_env
    state.save(fila, [_item("k1", status="blocked")])
    with pytest.raises(SystemExit, match="nada a publicar"):
        run("--publish")

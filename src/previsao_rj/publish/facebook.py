"""Publicação no Facebook (Página) — Reels e Stories pela API oficial da Meta.

Arquivo AUTOSSUFICIENTE: é o mesmo em todos os repositórios da rede de previsão
(só depende de `requests`). Não importa nada do pipeline do Instagram, para que
uma falha aqui nunca derrube a publicação lá — e vice-versa.

Fluxo (docs oficiais: developers.facebook.com/docs/video-api/guides/reels-publishing
e /docs/page-stories-api):

    start  -> POST /{page_id}/video_reels   upload_phase=start      -> video_id
    upload -> POST rupload.facebook.com/video-upload/{v}/{video_id} header file_url
    status -> GET  /{video_id}?fields=status  (espera o processamento)
    finish -> POST /{page_id}/video_reels   upload_phase=finish video_state=PUBLISHED

O MP4 NÃO é renderizado de novo nem reenviado: a Meta baixa o mesmo arquivo que
o Instagram já baixou (URL pública do Release do GitHub).

Configuração (env):
    FACEBOOK_PUBLISH_ENABLED   'true' liga; qualquer outra coisa = não publica
    FACEBOOK_REELS_ENABLED     padrão 'true'
    FACEBOOK_STORIES_ENABLED   padrão 'false'
    FACEBOOK_PAGE_ID           secret
    FACEBOOK_PAGE_ACCESS_TOKEN secret (token de PÁGINA, nunca o do Instagram)
    FACEBOOK_EXPECTED_PAGE     trava: nome ou @usuário esperado da Página
    FACEBOOK_GRAPH_VERSION     padrão v25.0

Estado: JSON versionado (padrão data/facebook_publicacoes.json), uma entrada por
chave única repo|facebook|page_id|tipo|dedupe_key. Nada que já foi `published`
é reenviado; `unknown` (a Meta pode ter aceitado) só sai por conferência.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests

BRT = timezone(timedelta(hours=-3))
DEFAULT_STATE = "data/facebook_publicacoes.json"
DEFAULT_VERSION = "v25.0"
REEL_MAX_S = 90
STORY_MAX_S = 60
MIN_S = 3

# ----------------------------------------------------------------- erros


class FacebookError(RuntimeError):
    """Erro já classificado. `transient` diz se vale tentar de novo."""

    def __init__(self, message: str, *, transient: bool, code: int | None = None,
                 kind: str = "api") -> None:
        super().__init__(message)
        self.transient = transient
        self.code = code
        self.kind = kind


# Códigos da Graph API (developers.facebook.com/docs/graph-api/guides/error-handling)
AUTH_CODES = {102, 190, 463, 467}                 # token inválido/expirado
PERMISSION_CODES = {10, 200, 210, 220, 230, 299}  # permissão insuficiente
RATE_CODES = {4, 17, 32, 613, 80001, 80002, 80005}
TRANSIENT_CODES = {1, 2, 6000, 6001}


def _redact(text: str) -> str:
    """Tira qualquer coisa parecida com token antes de ir para log/estado."""
    text = re.sub(r"(access_token=)[^&\s\"']+", r"\1***", str(text))
    text = re.sub(r"(OAuth\s+)[A-Za-z0-9_\-\.]+", r"\1***", text)
    return re.sub(r"EAA[A-Za-z0-9]{20,}", "EAA***", text)


def classify(status: int, body: Any) -> FacebookError:
    err = (body or {}).get("error", {}) if isinstance(body, dict) else {}
    code = err.get("code")
    msg = _redact(f"HTTP {status} code={code} sub={err.get('error_subcode')} "
                  f"{err.get('type', '')}: {err.get('message', '')}")
    if code in AUTH_CODES:
        return FacebookError("TOKEN: " + msg, transient=False, code=code, kind="auth")
    if code in PERMISSION_CODES:
        return FacebookError("PERMISSÃO: " + msg, transient=False, code=code, kind="permission")
    if code in RATE_CODES:
        return FacebookError("LIMITE: " + msg, transient=True, code=code, kind="rate")
    if code == 100 or status == 404:
        return FacebookError("ID/PARÂMETRO: " + msg, transient=False, code=code, kind="param")
    if code in TRANSIENT_CODES or status >= 500 or err.get("is_transient"):
        return FacebookError("INSTABILIDADE: " + msg, transient=True, code=code, kind="transient")
    return FacebookError(msg, transient=False, code=code)


def with_retry(fn: Callable[[], Any], *, attempts: int = 4, base: float = 10.0,
               sleep: Callable[[float], None] | None = None) -> Any:
    """Tenta de novo só o que é transitório, com espera progressiva (10, 30, 90s)."""
    for n in range(1, attempts + 1):
        try:
            return fn()
        except requests.RequestException as exc:  # rede
            last: Exception = FacebookError("REDE: " + _redact(repr(exc)), transient=True,
                                            kind="network")
        except FacebookError as exc:
            last = exc
        if not getattr(last, "transient", False) or n == attempts:
            raise last
        wait = base * (3 ** (n - 1))
        print(f"[facebook] tentativa {n} falhou ({last}); nova tentativa em {wait:.0f}s",
              file=sys.stderr)
        (sleep or time.sleep)(wait)
    raise RuntimeError("inalcançável")


# ------------------------------------------------------------- configuração


def enabled(flag: str, default: str = "false") -> bool:
    return (os.environ.get(flag) or default).strip().lower() == "true"


class Config:
    def __init__(self) -> None:
        self.page_id = (os.environ.get("FACEBOOK_PAGE_ID") or "").strip()
        self.token = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
        self.version = (os.environ.get("FACEBOOK_GRAPH_VERSION") or DEFAULT_VERSION).strip()
        self.expected = (os.environ.get("FACEBOOK_EXPECTED_PAGE") or "").strip().lstrip("@")
        if not self.page_id or not self.token:
            raise FacebookError("FACEBOOK_PAGE_ID/FACEBOOK_PAGE_ACCESS_TOKEN ausentes",
                                transient=False, kind="config")
        if not self.expected:
            raise FacebookError("FACEBOOK_EXPECTED_PAGE ausente: trava de destino obrigatória",
                                transient=False, kind="config")

    @property
    def graph(self) -> str:
        return f"https://graph.facebook.com/{self.version}"

    @property
    def rupload(self) -> str:
        return f"https://rupload.facebook.com/video-upload/{self.version}"


class Client:
    def __init__(self, cfg: Config, session: requests.Session | None = None) -> None:
        self.cfg = cfg
        self.http = session or requests.Session()

    def _call(self, method: str, url: str, **kw: Any) -> dict:
        r = self.http.request(method, url, timeout=60, **kw)
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code >= 400 or (isinstance(body, dict) and "error" in body):
            raise classify(r.status_code, body)
        return body

    def get(self, path: str, **params: Any) -> dict:
        params["access_token"] = self.cfg.token
        return with_retry(lambda: self._call("GET", f"{self.cfg.graph}/{path}", params=params))

    def post(self, path: str, **data: Any) -> dict:
        data["access_token"] = self.cfg.token
        return with_retry(lambda: self._call("POST", f"{self.cfg.graph}/{path}", data=data))

    # ---- verificações

    def verify_destination(self) -> dict:
        """Token é de PÁGINA e da página certa; nome/usuário batem com a trava."""
        me = self.get("me", fields="id,name")
        if str(me.get("id")) != self.cfg.page_id:
            raise FacebookError("DESTINO BLOQUEADO: o token não pertence a FACEBOOK_PAGE_ID",
                                transient=False, kind="destination")
        page = self.get(self.cfg.page_id, fields="id,name,username,link")
        wanted = self.cfg.expected.casefold()
        names = {(page.get("name") or "").casefold(), (page.get("username") or "").casefold()}
        if wanted not in names:
            raise FacebookError(f"DESTINO BLOQUEADO: página={page.get('name')!r}/"
                                f"{page.get('username')!r}, esperado={self.cfg.expected!r}",
                                transient=False, kind="destination")
        return page

    # ---- vídeo

    def _upload(self, edge: str, video_url: str) -> str:
        start = self.post(f"{self.cfg.page_id}/{edge}", upload_phase="start")
        video_id = str(start["video_id"])

        def send() -> dict:
            return self._call("POST", f"{self.cfg.rupload}/{video_id}", headers={
                "Authorization": f"OAuth {self.cfg.token}", "file_url": video_url})
        with_retry(send)
        return video_id

    def status(self, video_id: str) -> dict:
        return self.get(video_id, fields="status").get("status", {})

    def wait_processed(self, video_id: str, timeout_s: int = 600, every: int = 10,
                       sleep: Callable[[float], None] | None = None) -> dict:
        end = time.time() + timeout_s
        while True:
            st = self.status(video_id)
            up = (st.get("uploading_phase") or {}).get("status")
            proc = st.get("processing_phase") or {}
            if st.get("video_status") == "error" or proc.get("status") == "error":
                raise FacebookError("VÍDEO REJEITADO: " + _redact(json.dumps(proc.get("error") or st)),
                                    transient=False, kind="rejected")
            if up == "complete":
                # O finish pode ser chamado com o upload completo; o
                # processamento termina do lado da Meta e é conferido em confirm().
                return st
            if time.time() > end:
                raise FacebookError("PROCESSAMENTO: tempo esgotado esperando o upload",
                                    transient=True, kind="timeout")
            (sleep or time.sleep)(every)

    def publish_reel(self, video_url: str, description: str) -> dict:
        video_id = self._upload("video_reels", video_url)
        self.wait_processed(video_id)
        self.post(f"{self.cfg.page_id}/video_reels", upload_phase="finish",
                  video_id=video_id, video_state="PUBLISHED", description=description)
        return {"video_id": video_id}

    def publish_story(self, video_url: str) -> dict:
        video_id = self._upload("video_stories", video_url)
        self.wait_processed(video_id)
        r = self.post(f"{self.cfg.page_id}/video_stories", upload_phase="finish",
                      video_id=video_id)
        return {"video_id": video_id, "post_id": r.get("post_id")}

    def confirm(self, video_id: str) -> dict:
        """Confirmação independente: a Meta diz que o vídeo foi publicado?"""
        info = self.get(video_id, fields="status,permalink_url,published")
        pub = ((info.get("status") or {}).get("publishing_phase") or {}).get("status")
        info["confirmed"] = bool(info.get("published")) or pub == "complete"
        return info


# ------------------------------------------------------------------ estado


def unique_key(repo: str, page_id: str, kind: str, dedupe_key: str) -> str:
    return "|".join([repo, "facebook", page_id, kind, dedupe_key])


def load_state(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_state(path: str | Path, data: dict[str, dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def _now() -> str:
    return datetime.now(BRT).isoformat(timespec="seconds")


# ---------------------------------------------------------- texto (Facebook)

CTAS = [
    "Compartilhe com quem mora nessa região.",
    "Qual cidade você quer ver na próxima previsão?",
    "Como está o tempo na sua cidade?",
    "Envie para quem precisa sair de casa amanhã.",
    "Siga nossa página para acompanhar a previsão todos os dias.",
]
CTA_SERRA = "Envie para quem vai dirigir na Via Dutra nessa semana."
_IG_ONLY = re.compile(r"(link na bio|na bio|salve (este|esse) reel|salva (pra|para) depois|"
                      r"ative as notificações do reels?)", re.I)


def facebook_caption(ig_caption: str, dedupe_key: str, *, max_hashtags: int = 3) -> str:
    """Adapta a legenda do Instagram ao Facebook sem inventar dado.

    Mantém cidades, temperaturas, validade e avisos (o texto meteorológico é o
    mesmo); tira chamadas que só fazem sentido no Instagram, limita hashtags e
    troca o CTA final por um da lista, escolhido de forma determinística pela
    chave (alterna sem repetir em sequência e é igual em reexecuções).
    """
    serra = "serra das araras" in ig_caption.casefold()
    lines = []
    for line in ig_caption.splitlines():
        if _IG_ONLY.search(line):
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines).strip()
    tags = re.findall(r"#\w+", text)
    for t in tags[max_hashtags:]:
        text = re.sub(rf"\s*{re.escape(t)}\b", "", text, count=1)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if serra:
        cta = CTA_SERRA
    else:
        idx = int(hashlib.sha256(dedupe_key.encode()).hexdigest(), 16) % len(CTAS)
        cta = CTAS[idx]
    if cta.casefold() not in text.casefold():
        text = f"{text}\n\n{cta}"
    return text


def duration_s(local_file: str | None) -> float | None:
    if not local_file or not Path(local_file).exists():
        return None
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", local_file],
                             capture_output=True, text=True, timeout=60, check=True)
        return float(out.stdout.strip())
    except Exception:  # noqa: BLE001 — sem ffprobe a Meta valida sozinha
        return None


# --------------------------------------------------------------- orquestração


def run(kind: str, video_url: str, ig_caption: str, dedupe_key: str, *, repo: str,
        state_path: str = DEFAULT_STATE, local_file: str | None = None,
        client: Client | None = None, confirm_every: float = 10.0) -> dict:
    """Publica um item numa plataforma, uma vez só. Devolve a entrada do estado."""
    flag = {"reel": ("FACEBOOK_REELS_ENABLED", "true"),
            "story": ("FACEBOOK_STORIES_ENABLED", "false")}[kind]
    if not enabled("FACEBOOK_PUBLISH_ENABLED"):
        return {"status": "disabled", "reason": "FACEBOOK_PUBLISH_ENABLED != true"}
    if not enabled(*flag):
        return {"status": "disabled", "reason": f"{flag[0]} != true"}

    client = client or Client(Config())
    page_id = client.cfg.page_id
    key = unique_key(repo, page_id, kind, dedupe_key)
    data = load_state(state_path)
    entry = data.get(key, {})

    if entry.get("status") == "published":
        print(f"[facebook] {kind} já publicado ({entry.get('video_id')}); nada a fazer")
        return entry
    if entry.get("status") in {"unknown", "publishing"} and entry.get("video_id"):
        # Execução anterior pode ter publicado: pergunta à Meta antes de repetir.
        info = client.confirm(entry["video_id"])
        if info["confirmed"]:
            entry.update(status="published", confirmed_at=_now(),
                         permalink=info.get("permalink_url"))
            data[key] = entry
            save_state(state_path, data)
            return entry

    dur = duration_s(local_file)
    limit = REEL_MAX_S if kind == "reel" else STORY_MAX_S
    if dur is not None and not (MIN_S <= dur <= limit):
        entry.update(status="skipped", reason=f"duração {dur:.1f}s fora de {MIN_S}-{limit}s",
                     updated_at=_now())
        data[key] = entry
        save_state(state_path, data)
        return entry

    page = client.verify_destination()
    caption = facebook_caption(ig_caption, dedupe_key)
    entry.update(status="publishing", page=page.get("name"), video_url=video_url,
                 caption_sha=hashlib.sha256(caption.encode()).hexdigest()[:16],
                 attempts=int(entry.get("attempts", 0)) + 1, updated_at=_now())
    entry.pop("error", None)
    data[key] = entry
    save_state(state_path, data)

    try:
        result = client.publish_reel(video_url, caption) if kind == "reel" \
            else client.publish_story(video_url)
    except FacebookError as exc:
        # Antes do finish não existe post: pode tentar de novo depois.
        entry.update(status="failed", error=str(exc), error_kind=exc.kind,
                     retryable=exc.transient, updated_at=_now())
        save_state(state_path, data)
        raise
    except Exception as exc:  # noqa: BLE001
        entry.update(status="unknown", error=_redact(repr(exc)), updated_at=_now())
        save_state(state_path, data)
        raise

    entry.update(result, status="unknown", updated_at=_now())
    save_state(state_path, data)
    try:
        # A Meta processa depois do finish: confere por até ~5 min.
        for _ in range(30):
            info = client.confirm(result["video_id"])
            if info["confirmed"] or kind == "story":
                break
            time.sleep(confirm_every)
    except FacebookError as exc:
        entry.update(error="confirmação: " + str(exc))
        save_state(state_path, data)
        raise
    entry.update(status="published" if info["confirmed"] or kind == "story" else "unknown",
                 permalink=info.get("permalink_url"), published_at=_now())
    save_state(state_path, data)
    return entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Publica no Facebook o MP4 já hospedado.")
    ap.add_argument("--kind", choices=["reel", "story"], default="reel")
    ap.add_argument("--video-url", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--dedupe-key", required=True)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "local"))
    ap.add_argument("--state", default=DEFAULT_STATE)
    ap.add_argument("--local-file", help="MP4 local, só para conferir a duração")
    a = ap.parse_args(argv)
    caption = Path(a.caption_file).read_text(encoding="utf-8").strip()
    try:
        entry = run(a.kind, a.video_url, caption, a.dedupe_key, repo=a.repo,
                    state_path=a.state, local_file=a.local_file)
    except FacebookError as exc:
        print(f"[facebook] FALHA ({exc.kind}): {exc}", file=sys.stderr)
        return 1
    shown = {k: v for k, v in entry.items() if k not in {"video_url"}}
    print("[facebook]", json.dumps(shown, ensure_ascii=False))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Facebook ({a.kind}): `{entry.get('status')}`\n")
            if entry.get("permalink"):
                fh.write(f"- link: {entry['permalink']}\n")
            if entry.get("reason"):
                fh.write(f"- motivo: {entry['reason']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

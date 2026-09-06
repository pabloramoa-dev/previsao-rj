from __future__ import annotations
import os, time, requests, hashlib


def _cfg():
    user = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    version = os.environ.get("META_GRAPH_VERSION", "v26.0")
    expected = os.environ.get("EXPECTED_IG_USERNAME", "previsaorj").lstrip("@").casefold()
    if not user or not token:
        raise RuntimeError("IG_USER_ID/IG_ACCESS_TOKEN ausentes")
    return user, token, version, expected


def base_url(version: str) -> str:
    # Centralizado para permitir regressão controlada de versão/host.
    return f"https://graph.instagram.com/{version}"


def verify_destination() -> dict:
    user, token, version, expected = _cfg()
    r = requests.get(f"{base_url(version)}/{user}", params={"fields":"id,username","access_token":token}, timeout=30)
    r.raise_for_status()
    data = r.json()
    got = (data.get("username") or "").casefold()
    if got != expected:
        raise RuntimeError(f"DESTINO BLOQUEADO: username retornado={got!r}, esperado={expected!r}")
    return data


def create_reel(video_url: str, caption: str) -> str:
    user, token, version, _ = _cfg()
    r = requests.post(f"{base_url(version)}/{user}/media", data={
        "media_type":"REELS", "video_url":video_url, "caption":caption,
        "share_to_feed":"true", "access_token":token}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def wait_ready(container_id: str, timeout_s: int = 300) -> None:
    _, token, version, _ = _cfg()
    end = time.time() + timeout_s
    while time.time() < end:
        r = requests.get(f"{base_url(version)}/{container_id}", params={"fields":"status_code","access_token":token}, timeout=30)
        r.raise_for_status()
        state = r.json().get("status_code")
        if state == "FINISHED": return
        if state in {"ERROR","EXPIRED"}: raise RuntimeError(f"container {state}")
        time.sleep(10)
    raise TimeoutError("Instagram container não concluiu")


def publish(container_id: str) -> str:
    user, token, version, _ = _cfg()
    r = requests.post(f"{base_url(version)}/{user}/media_publish", data={"creation_id":container_id,"access_token":token}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def caption_hash(caption: str) -> str:
    return hashlib.sha256(" ".join(caption.split()).encode()).hexdigest()[:16]

def already_published_caption(caption: str, limit: int = 25) -> bool:
    """Consulta mídias recentes e bloqueia legenda equivalente em retry/reexecução."""
    user, token, version, _ = _cfg()
    r = requests.get(f"{base_url(version)}/{user}/media", params={
        "fields":"id,caption,timestamp", "limit":str(limit), "access_token":token}, timeout=30)
    r.raise_for_status()
    target = " ".join((caption or "").split()).casefold()
    for item in r.json().get("data", []):
        current = " ".join((item.get("caption") or "").split()).casefold()
        if current and current == target:
            return True
    return False

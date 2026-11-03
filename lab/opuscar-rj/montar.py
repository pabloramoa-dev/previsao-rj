#!/usr/bin/env python3
"""Pacote visual de telejornal/dados inspirado em lemo-opuscar News Package.
Preserva integralmente o video e o audio Kokoro originais do Bira.
Piloto isolado, com dados reais identificados e bloqueio de publicacao.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 540, 960, 30
ABERTURA = 1.8
FECHO = 1.5
INK = "#0b2234"
BLUE = "#112f48"
TEAL = "#27c6bb"
GOLD = "#ffce65"
WHITE = "#f8fcff"
PALE = "#bfd5df"
FONT_BASE = "/usr/share/fonts/truetype/dejavu/DejaVuSans"


def cmd(*args):
    subprocess.run([str(v) for v in args], check=True)


def probe(path):
    p = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)], text=True)
    return json.loads(p)


def validar_video(path):
    info = probe(path)
    videos = [s for s in info["streams"] if s["codec_type"] == "video"]
    audios = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or not audios:
        raise ValueError("O MP4 deve conter video e audio")
    v = videos[0]
    if (v["width"], v["height"], v["avg_frame_rate"]) != (1080, 1920, "30/1"):
        raise ValueError("O MP4 deve ser vertical 1080x1920, 30fps")
    if float(info["format"]["duration"]) <= 5:
        raise ValueError("O MP4 original nao esta completo")
    return float(info["format"]["duration"])


def extrair_painel(snapshot):
    """Nunca transforma ausência de previsão em zero nem cria valores fictícios."""
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot invalido")
    bloco = snapshot.get("forecast", {}).get("today", {})
    locais = bloco.get("locations", [])
    usados, linhas = set(), []
    for loc in locais:
        nome = str(loc.get("name", "")).strip()
        if not nome or nome.casefold() in usados:
            continue
        try:
            minimo = float(loc["min_c"])
            maximo = float(loc["max_c"])
            prob = float(loc["rain_probability_pct"])
        except (TypeError, ValueError, KeyError):
            continue
        if not all(math.isfinite(v) for v in (minimo, maximo, prob)):
            continue
        if minimo > maximo or not 0 <= prob <= 100:
            continue
        linhas.append({"nome": nome, "min": minimo, "max": maximo, "chuva": prob})
        usados.add(nome.casefold())
        if len(linhas) == 4:
            break
    if len(linhas) < 2:
        raise ValueError("Faltam pelo menos dois locais com dados meteorologicos confiaveis")
    data = str(bloco.get("date") or snapshot.get("generated_at") or "")[:10]
    try:
        dt.date.fromisoformat(data)
    except ValueError as exc:
        raise ValueError("Sem data valida para identificar a previsao") from exc
    if str(snapshot.get("source", "")).startswith("fixture"):
        raise ValueError("Este workflow usa somente coleta real; fixture bloqueada")
    return data, linhas


@lru_cache(maxsize=24)
def fonte(tam, bold=False):
    return ImageFont.truetype(FONT_BASE + ("-Bold" if bold else "") + ".ttf", tam)


def escrever(d, xy, msg, tam, cor=WHITE, bold=False):
    d.text(xy, msg, font=fonte(tam, bold), fill=cor)


def fundo(d, t):
    d.rectangle((0, 0, W, H), fill=INK)
    d.rectangle((0, 0, W, 12), fill=GOLD)
    # Linhas de scanner: motion graphics 2D deterministico, sem dependencia GPU.
    x = int((t * 185) % (W + 150)) - 150
    d.polygon([(x, 0), (x + 85, 0), (x - 40, H), (x - 110, H)],
              fill="#102b40")
    for y in range(160, 850, 90):
        d.line((0, y, W, y), fill="#1a3a52", width=1)
    d.rounded_rectangle((24, 32, 516, 117), radius=15, fill=BLUE)
    escrever(d, (41, 47), "PREVISÃO RJ", 32, WHITE, True)
    escrever(d, (382, 65), "AO VIVO*", 14, GOLD, True)
    d.rectangle((26, 131, 514, 135), fill=TEAL)


def selo(d):
    d.rounded_rectangle((18, 897, 522, 943), radius=9, fill="#a32e33")
    escrever(d, (33, 909), "PILOTO VISUAL • NÃO PUBLICAR", 19, WHITE, True)


def quadro(t, data, linhas):
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    fundo(d, t)
    escrever(d, (30, 176), "GIRO METROPOLITANO", 26, GOLD, True)
    escrever(d, (30, 219), "O TEMPO EM MOVIMENTO", 24, WHITE, True)
    escrever(d, (30, 262), "Dados: " + data + "  •  °C e chance de chuva", 15, PALE)
    # Cartoes deslizantes e barras de chance de chuva: linguagem data-storytelling.
    for i, local in enumerate(linhas):
        entrada = min(1.0, max(0.0, (t - 0.15 - i * 0.17) / 0.55))
        x = int(28 + (1 - entrada) * 80)
        y = 319 + i * 128
        if entrada <= 0:
            continue
        d.rounded_rectangle((x, y, 512, y + 113), radius=14, fill=BLUE)
        d.rounded_rectangle((x + 2, y + 2, x + 11, y + 111), radius=4, fill=TEAL)
        nome = local["nome"].upper()
        tam = 22 if len(nome) <= 18 else 18
        escrever(d, (x + 21, y + 12), nome[:28], tam, WHITE, True)
        escrever(d, (x + 23, y + 51), f'{local["min"]:g}° / {local["max"]:g}°', 21, GOLD, True)
        escrever(d, (x + 267, y + 55), f'{local["chuva"]:g}% chuva', 17, WHITE)
        d.rounded_rectangle((x + 22, y + 88, x + 449, y + 99),
                            radius=5, fill="#35546a")
        largura = int(427 * local["chuva"] / 100 * entrada)
        if largura >= 2:
            d.rounded_rectangle((x + 22, y + 88, x + 22 + largura, y + 99),
                                radius=5, fill=TEAL)
    escrever(d, (30, 849), "EDIÇÃO ESPECIAL  /  BIRA DO TEMPO", 19, GOLD, True)
    selo(d)
    return im


def despedida(t, data):
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    fundo(d, t)
    progresso = min(1.0, max(0.0, t / 0.55))
    faixa = int(450 * progresso)
    d.rectangle((42, 280, 42 + faixa, 295), fill=TEAL)
    escrever(d, (42, 345), "BIRA DO TEMPO", 36, GOLD, True)
    escrever(d, (42, 430), "E NO SEU BAIRRO?", 31, WHITE, True)
    escrever(d, (42, 495), "Conte nos comentários", 23, PALE)
    escrever(d, (42, 532), "ou mande uma DM.", 23, PALE)
    d.rounded_rectangle((40, 640, 500, 734), radius=20, fill=TEAL)
    escrever(d, (62, 672), "@PREVISAORJ", 32, INK, True)
    escrever(d, (42, 818), "Previsão consultada: " + data, 18, PALE)
    selo(d)
    return im


def renderizar_cartao(destino, tipo, data, linhas):
    dur = ABERTURA if tipo == "abertura" else FECHO
    frames = round(dur * FPS)
    fade = max(0.0, dur - 0.33)
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
          "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
          "-r", str(FPS), "-i", "pipe:0",
          "-f", "lavfi", "-i",
          f"sine=frequency={660 if tipo == 'abertura' else 440}:sample_rate=48000:duration={dur}",
          "-filter_complex",
          f"[0:v]scale=1080:1920:flags=bicubic,format=yuv420p[v];"
          f"[1:a]volume=0.035,afade=t=out:st={fade:.2f}:d=0.33[a]",
          "-map", "[v]", "-map", "[a]", "-frames:v", str(frames),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
          "-profile:v", "main", "-level:v", "4.0", "-pix_fmt", "yuv420p",
          "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
          "-movflags", "+faststart", str(destino)]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    try:
        for f in range(frames):
            img = quadro(f / FPS, data, linhas) if tipo == "abertura" else despedida(f / FPS, data)
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("Falha no cartao Opuscar")
    if not destino.exists() or destino.stat().st_size < 15000:
        raise RuntimeError("Cartao incompleto")


def montar(original, snapshot, saida):
    original = Path(original).resolve()
    saida = Path(saida).resolve()
    if original == saida:
        raise ValueError("Nunca sobrescrever video original no piloto")
    dur_original = validar_video(original)
    data, cidades = extrair_painel(json.loads(Path(snapshot).read_text(encoding="utf-8")))
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="opuscar-rj-") as temporario:
        pasta = Path(temporario)
        inicio, fim = pasta / "abertura.mp4", pasta / "fecho.mp4"
        renderizar_cartao(inicio, "abertura", data, cidades)
        renderizar_cartao(fim, "fecho", data, cidades)
        playlist = pasta / "playlist.txt"
        playlist.write_text("\n".join("file '" + str(p) + "'"
                                      for p in (inicio, original, fim)) + "\n",
                            encoding="utf-8")
        cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", playlist, "-map", "0:v:0",
            "-map", "0:a:0", "-c", "copy", "-movflags", "+faststart", saida)
    dur_final = validar_video(saida)
    if abs(dur_final - (ABERTURA + dur_original + FECHO)) > 1.0:
        raise ValueError("Concat alterou a duracao do programa")
    cmd("ffmpeg", "-v", "error", "-i", saida, "-f", "null", "-")
    previo = saida.with_name(saida.stem + "_preview_720p.mp4")
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", saida, "-vf", "scale=720:1280", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", previo)
    capa = saida.parent / "CAPA_OPUSCAR_RJ.jpg"
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "1.35", "-i", saida, "-frames:v", "1", "-q:v", "2", capa)
    resumo = {"video": str(saida), "apresentador": "Bira do Tempo",
              "estilo": "Lemo Opuscar (News Package + Data Storytelling), adaptado",
              "data": data, "locais": [p["nome"] for p in cidades],
              "duracao_s": round(dur_final, 2), "publicado": False,
              "fonte": "snapshot ao vivo do Previsao RJ"}
    saida.with_suffix(".json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False))
    return saida


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--saida", required=True)
    args = parser.parse_args()
    montar(args.original, args.snapshot, args.saida)

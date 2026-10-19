#!/usr/bin/env python3
"""Acabamento editorial CPU para MP4 do personagem ORIGINAL (sem TTS, IA ou GPU).

Roda somente quando a pauta contém "interatividade". O vídeo e a voz originais
tocam completos; acrescenta um cartão curto de enquete/pergunta ao final.
B-roll é um clipe local com licença e crédito; nunca consulta APIs externas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

def _run(args):
    return subprocess.run([str(x) for x in args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)

def _probe(path):
    data = json.loads(_run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                            "-of", "json", path]).stdout)
    video = next((x for x in data["streams"] if x["codec_type"] == "video"), None)
    audio = next((x for x in data["streams"] if x["codec_type"] == "audio"), None)
    if not video or not audio:
        raise ValueError("O render original precisa ter vídeo e áudio")
    duration = float(data["format"]["duration"])
    rate = video.get("avg_frame_rate", "30/1").split("/")
    fps = max(15, min(60, round(float(rate[0]) / max(1, float(rate[1])))))
    return dict(duration=duration, width=int(video["width"]), height=int(video["height"]),
                fps=fps, video_codec=video["codec_name"], audio_codec=audio["codec_name"])

def _asset(root, name):
    if not name:
        return None
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Apoio precisa ser arquivo local existente dentro do repositório")
    return path

def validate(config, root):
    if not isinstance(config, dict):
        raise ValueError("interatividade precisa ser objeto JSON")
    if config.get("modo", "pergunta") not in ("pergunta", "quiz", "misterio", "mito_verdade"):
        raise ValueError("modo de interação inválido")
    question = config.get("pergunta", "")
    if not isinstance(question, str) or not 8 <= len(question.strip()) <= 135:
        raise ValueError("pergunta deve ter entre 8 e 135 caracteres")
    options = config.get("opcoes", [])
    if not isinstance(options, list) or len(options) > 4 or any(
        not isinstance(o, str) or not 1 <= len(o) <= 75 for o in options
    ):
        raise ValueError("opcoes inválidas")
    if options and len(options) < 2:
        raise ValueError("forneça pelo menos duas opções")
    answer = config.get("resposta")
    if answer is not None and (not isinstance(answer, str) or not 1 <= len(answer) <= 100):
        raise ValueError("resposta inválida")
    if (config.get("modo") == "quiz") and not options:
        raise ValueError("quiz exige alternativas")
    seconds = config.get("segundos", 2.8)
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 2 <= seconds <= 4:
        raise ValueError("segundos deve ser de 2 a 4")
    video = config.get("broll_video")
    image = config.get("broll_imagem")
    if video and image:
        raise ValueError("selecione video OU imagem de apoio")
    if options and (video or image):
        raise ValueError("quiz com alternativas nao admite B-roll sobre o texto")
    if (video or image) and not str(config.get("credito", "")).strip():
        raise ValueError("b-roll exige credito e licença")
    if video:
        _asset(root, video)
    if image:
        _asset(root, image)
    return config

def _font(sz, bold=False):
    options = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    return ImageFont.truetype(next(x for x in options if Path(x).exists()), sz)

def _lines(draw, text, f, max_width):
    lines, row = [], ""
    for token in str(text).split():
        candidate = (row + " " + token).strip()
        if row and draw.textbbox((0, 0), candidate, font=f)[2] > max_width:
            lines.append(row)
            row = token
        else:
            row = candidate
    if row:
        lines.append(row)
    return lines

def _write(draw, text, xy, width, height, base, fill, bold=False):
    x, y = xy
    for size in range(base, 19, -3):
        face = _font(size, bold)
        lines = _lines(draw, text, face, width)
        if len(lines)*(size+12) <= height and all(
            draw.textbbox((0, 0), line, font=face)[2] <= width for line in lines
        ):
            for line in lines:
                draw.text((x, y), line, font=face, fill=fill)
                y += size + 12
            return
    raise ValueError("Texto da interação não cabe no cartão")

def _poster(last_frame, output, config, width, height, broll_image=None):
    with Image.open(last_frame) as opened:
        base = ImageOps.fit(opened.convert("RGB"), (width, height))
    base = ImageEnhance.Brightness(base).enhance(.38)
    draw = ImageDraw.Draw(base)
    scale = width / 1080
    def b(xy): return tuple(round(x*scale) for x in xy)
    draw.rounded_rectangle(b((65, 215, 1015, 1700)), radius=round(45*scale),
                           fill=(26, 24, 36), outline=(243, 198, 86), width=max(2, round(5*scale)))
    accent = "#ffd75f"
    _write(draw, "SUA VEZ DE PARTICIPAR", b((112, 280)), round(815*scale),round(95*scale),
           round(40*scale),accent, True)
    _write(draw, config["pergunta"], b((112, 430)), round(810*scale), round(325*scale),
           round(67*scale), "white", True)
    options = config.get("opcoes") or []
    for i, opt in enumerate(options[:4]):
        posy = 825 + i * 130
        draw.rounded_rectangle(b((105,posy-15,965,posy+104)),radius=round(23*scale),fill="#3c3950")
        _write(draw, f"{chr(65+i)} — {opt}", b((144,posy+15)), round(760*scale),
               round(83*scale), round(39*scale), "white")
    if broll_image:
        # Use B-roll como reforço na área vazia, nunca em cima da fala/legenda original.
        with Image.open(broll_image) as im:
            art = ImageOps.contain(im.convert("RGB"), b((735,380)))
        base.paste(art, (round(width/2-art.width/2),round(1220*scale)))
    _write(draw, "COMENTE SUA RESPOSTA", b((130, 1540)), round(805*scale),
           round(84*scale), round(39*scale), accent, True)
    base.save(output)

def finish(video_file, config, root, *, max_total=180, replace=True):
    """Só renderiza se a pauta declara interatividade; retorna manifesto verificável."""
    original = Path(video_file).resolve()
    root = Path(root).resolve()
    cfg = validate(config, root)
    if not original.is_file():
        raise FileNotFoundError(original)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg e ffprobe obrigatórios; GPU desnecessária")
    target_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    report_file = original.with_suffix(".interatividade.json")
    if report_file.exists():
        old = json.loads(report_file.read_text(encoding="utf-8"))
        if old.get("configuration_sha256") == target_hash and old.get("file_sha256") == hashlib.sha256(original.read_bytes()).hexdigest():
            return dict(old, reused=True)
        raise RuntimeError("O MP4 já foi finalizado com outra configuração; renderize o episódio original novamente")
    info = _probe(original)
    seconds = float(cfg.get("segundos", 2.8))
    answer_seconds = 1.6 if cfg.get("resposta") else 0
    final_seconds = seconds + answer_seconds
    if info["duration"] + final_seconds > max_total:
        report = dict(applied=False, reason="duracao_maxima", duration_original=info["duration"],
                      max_seconds=max_total, configuration_sha256=target_hash)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return report
    with tempfile.TemporaryDirectory(prefix="acabamento-original-") as td:
        tmp = Path(td)
        frame = tmp / "ultimo_quadro.png"
        poster = tmp / "cartao.png"
        destination = tmp / "entrega.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.5", "-i", original,
              "-frames:v", "1", frame])
        broll_image = _asset(root, cfg.get("broll_imagem"))
        broll_video = _asset(root, cfg.get("broll_video"))
        _poster(frame, poster, cfg, info["width"], info["height"], broll_image)
        inputs = ["-i", original, "-loop", "1", "-framerate", info["fps"], "-i", poster]
        parts = [f"[0:v]fps={info['fps']},setsar=1,setpts=PTS-STARTPTS[orig]",
                 f"[1:v]trim=duration={seconds:.3f},fps={info['fps']},setpts=PTS-STARTPTS,setsar=1[card]"]
        card_label = "[card]"
        if broll_video:
            # B-roll local em MOVIMENTO, na área reservada no cartão, jamais
            # sobre a boca da personagem ou sobre legendas narradas.
            n = 2
            bw, bh = round(info["width"] * .66), round(info["height"] * .20)
            by = round(info["height"] * .60)
            inputs += ["-stream_loop", "-1", "-i", broll_video]
            parts.append(f"[{n}:v]fps={info['fps']},scale={bw}:{bh}:force_original_aspect_ratio=decrease,"
                         f"pad={bw}:{bh}:(ow-iw)/2:(oh-ih)/2:color=0x262634,setsar=1,"
                         f"trim=duration={seconds:.3f},setpts=PTS-STARTPTS[broll]")
            parts.append(f"[card][broll]overlay=x=(W-w)/2:y={by}:shortest=1[card_broll]")
            card_label = "[card_broll]"
        labels = "[orig]" + card_label
        if cfg.get("resposta"):
            answer_poster = tmp / "resposta.png"
            answer_cfg = dict(cfg, pergunta="RESPOSTA: " + cfg["resposta"], opcoes=[])
            _poster(frame, answer_poster, answer_cfg, info["width"], info["height"])
            n = 3 if broll_video else 2
            inputs += ["-loop", "1", "-framerate", info["fps"], "-i", answer_poster]
            parts.append(f"[{n}:v]trim=duration={answer_seconds:.3f},fps={info['fps']},setpts=PTS-STARTPTS,setsar=1[answer]")
            labels += "[answer]"
        filter_video = ";".join(parts) + ";" + labels + f"concat=n={3 if cfg.get('resposta') else 2}:v=1:a=0[v]"
        _run(["ffmpeg", "-y", "-v", "error", *inputs,
              "-filter_complex", filter_video, "-map", "[v]", "-map", "0:a:0",
              "-af", "apad", "-t", f"{info['duration'] + final_seconds:.3f}",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
              "-movflags", "+faststart", destination])
        check = _probe(destination)
        if check["duration"] < info["duration"]+final_seconds-.5 or (check["width"],check["height"]) != (info["width"],info["height"]):
            raise RuntimeError("QA: MP4 final incompleto ou resolução alterada")
        if replace:
            os.replace(destination, original)
        else:
            original = original.with_name(original.stem + "_interativo.mp4")
            shutil.copy2(destination, original)
    result = dict(applied=True, gpu=False, paid_api=False, original_character=True,
                  original_voice=True, duration_original=round(info["duration"],2),
                  duration_final=round(check["duration"],2), format=cfg.get("modo","pergunta"),
                  question=cfg["pergunta"], licensed_broll=bool(cfg.get("broll_video") or cfg.get("broll_imagem")),
                  media_credit=cfg.get("credito"), configuration_sha256=target_hash,
                  file_sha256=hashlib.sha256(original.read_bytes()).hexdigest(), output=str(original))
    report_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

def apply_from_metadata(video, metadata, root):
    """Integração dos motores originais. Sem interatividade, mantém MP4 intacto."""
    if not isinstance(metadata, dict) or not metadata.get("interatividade"):
        return dict(applied=False, reason="episodio_nao_interativo")
    enabled = os.getenv("NATIVE_ENGAGEMENT_ENABLED", "true").strip().lower() in ("true","1","yes","sim")
    if not enabled:
        return dict(applied=False, reason="desativado_por_env")
    return finish(video, metadata["interatividade"], root)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    a=p.parse_args()
    meta=json.loads(a.spec.read_text(encoding="utf-8"))
    report=apply_from_metadata(a.video, meta, a.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
if __name__=="__main__":
    main()

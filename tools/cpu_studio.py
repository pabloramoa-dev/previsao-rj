#!/usr/bin/env python3
"""Estudio CPU: cria MP4 vertical a partir de cenas JSON, sem GPU nem API.
Nao publica. Aceita voz WAV/MP3 por cena, imagem PNG/JPG e fallback espeak-ng.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE = (1080, 1920)
FPS = 25
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PALETTES = {
    "nina": ("#24102f", "#f6c94d", "#fff3ee"),
    "guru": ("#161a32", "#f2d17a", "#f5f1e7"),
    "mengao": ("#1b1117", "#f44352", "#fff1ec"),
    "tempo": ("#102b42", "#52d6e5", "#f7f9ff"),
    "sabio": ("#25362d", "#dfbd79", "#fff6e8"),
}

def run(cmd):
    subprocess.run([str(a) for a in cmd], check=True)

def font(px, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, px)

def wrap(draw, text, face, max_width):
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        if not paragraph.strip():
            lines.append("")
            continue
        row = ""
        for token in paragraph.split():
            candidate = (row + " " + token).strip()
            if row and draw.textbbox((0, 0), candidate, font=face)[2] > max_width:
                lines.append(row)
                row = token
            else:
                row = candidate
        lines.append(row)
    return lines

def block(draw, text, y, *, size, color, width=880, maxlines=6, x=100, gap=13, bold=False):
    face = font(size, bold)
    lines = wrap(draw, text, face, width)
    if len(lines) > maxlines:
        raise ValueError("Texto longo demais para o quadro: " + str(text)[:80])
    for line in lines:
        draw.text((x, y), line, fill=color, font=face, stroke_width=0)
        y += size + gap
    return y

def _local_path(spec_dir, value):
    if not value:
        return None
    path = (spec_dir / str(value)).resolve()
    if not path.is_file():
        raise ValueError("Arquivo local ausente: " + str(path))
    return path

def validate(spec, spec_dir):
    if not isinstance(spec, dict):
        raise ValueError("Roteiro precisa ser um objeto JSON")
    name = spec.get("name")
    scenes = spec.get("scenes")
    if not isinstance(name, str) or not 1 <= len(name) <= 55:
        raise ValueError("name obrigatorio, maximo 55 caracteres")
    if spec.get("style", "nina") not in PALETTES:
        raise ValueError("style desconhecido")
    if not isinstance(scenes, list) or not 2 <= len(scenes) <= 14:
        raise ValueError("sao necessarias entre 2 e 14 cenas")
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError("Cena nao e objeto JSON: " + str(i))
        if not isinstance(scene.get("title"), str) or not 1 <= len(scene["title"]) <= 95:
            raise ValueError("Titulo invalido na cena " + str(i))
        if not isinstance(scene.get("text"), str) or not 1 <= len(scene["text"]) <= 450:
            raise ValueError("Texto invalido na cena " + str(i))
        duration = scene.get("seconds", 4)
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or not 2 <= duration <= 18:
            raise ValueError("Duracao deve estar entre 2 e 18 segundos: " + str(i))
        if scene.get("video") and scene.get("image"):
            raise ValueError("Escolha image OU video para a mesma cena")
        if scene.get("video") and not str(scene.get("media_credit") or "").strip():
            raise ValueError("video exige media_credit (origem/licenca)")
        for key in ("image", "video", "voice_file"):
            if scene.get(key):
                _local_path(spec_dir, scene[key])
    return spec

def make_frame(spec, scene, number, path, spec_dir):
    bg, accent, fg = PALETTES[spec.get("style", "nina")]
    im = Image.new("RGB", SIZE, bg)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((65, 70, 1015, 162), radius=28, fill=accent)
    d.text((102, 88), spec["name"].upper(), font=font(39, True), fill=bg)
    d.text((880, 92), f"{number+1:02d}/{len(spec['scenes']):02d}", font=font(28), fill=bg)
    y = block(d, scene["title"], 270, size=70, color=fg, maxlines=3, bold=True)
    d.rounded_rectangle((68, 605, 1012, 1460), radius=36, fill="#ffffff")
    img_path = _local_path(spec_dir, scene.get("image"))
    if img_path:
        with Image.open(img_path) as original:
            art = ImageOps.contain(original.convert("RGBA"), (840, 410))
            im.paste(art, ((1080 - art.width)//2, 660), art)
    if img_path or scene.get("video"):
        ytxt = 1120
        tsize, maxlines = 44, 5
    else:
        ytxt = 750
        tsize, maxlines = 51, 9
    block(d, scene["text"], ytxt, size=tsize, color="#29202a", width=810, x=130, maxlines=maxlines)
    d.rounded_rectangle((70, 1535, 1010, 1685), radius=28, outline=accent, width=4)
    block(d, spec.get("footer", "Comente sua resposta e veja o proximo episodio."), 1575,
          size=30, color=fg, x=110, width=850, maxlines=2)
    d.rounded_rectangle((70, 1780, 1010, 1792), radius=6, fill=accent)
    d.rounded_rectangle((70, 1780, 70 + round(940*(number+1)/len(spec["scenes"])), 1792), radius=6, fill=fg)
    im.save(path)

def audio_duration(path):
    data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]))
    return float(data["format"]["duration"])

def make_voice(scene, work, index, spec_dir, tts):
    if scene.get("voice_file"):
        return _local_path(spec_dir, scene["voice_file"])
    if tts != "espeak":
        return None
    result = work / f"voice_{index}.wav"
    if not shutil.which("espeak-ng"):
        raise RuntimeError("espeak-ng necessario para --tts espeak")
    spoken = str(scene.get("voice_text") or (scene["title"] + ". " + scene["text"]))
    run(["espeak-ng", "-v", "pt-br", "-s", "155", "-w", result, spoken])
    return result

def render(spec, spec_dir, destination, tts):
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} nao instalado")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="estudio-cpu-") as temp:
        work = Path(temp)
        videos = []
        report = []
        for i, scene in enumerate(spec["scenes"]):
            frame = work / f"frame_{i}.png"
            clip = work / f"clip_{i}.mp4"
            make_frame(spec, scene, i, frame, spec_dir)
            voice = make_voice(scene, work, i, spec_dir, tts)
            duration = max(float(scene.get("seconds", 4)), audio_duration(voice) + .45 if voice else 0)
            video = _local_path(spec_dir, scene.get("video"))
            if voice:
                sources = ["-i", voice]
            else:
                sources = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            video_sources = ["-stream_loop", "-1", "-i", video] if video else []
            fade_out = max(duration-.22, .2)
            fade = f"fade=t=in:st=0:d=0.18,fade=t=out:st={fade_out:.3f}:d=0.18,format=yuv420p"
            if video:
                graph = ("[1:v]scale=840:410:force_original_aspect_ratio=decrease,"
                         "pad=840:410:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1[filme];"
                         f"[0:v][filme]overlay=120:660:shortest=0,{fade}[outv]")
                maps = ["-filter_complex", graph, "-map", "[outv]", "-map", "2:a:0"]
            else:
                maps = ["-vf", fade]
            run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", FPS, "-i", frame,
                 *video_sources, *sources, "-t", f"{duration:.3f}", *maps,
                 "-af", "apad", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                 "-r", FPS, "-c:a", "aac", "-ar", "48000", "-b:a", "128k", "-shortest", clip])
            videos.append(clip)
            report.append({"scene": i+1, "seconds": round(duration, 2), "narrated": bool(voice),
                           "has_image": bool(scene.get("image")), "has_video": bool(video),
                           "media_credit": scene.get("media_credit") if video else None})
        manifest = work / "concat.txt"
        manifest.write_text("".join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in videos), encoding="utf-8")
        tmp_out = destination.with_suffix(".rendering.mp4")
        try:
            run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", manifest,
                 "-c", "copy", "-movflags", "+faststart", tmp_out])
            info = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", tmp_out]))
            streams = info["streams"]
            v = next((s for s in streams if s["codec_type"] == "video"), None)
            a = next((s for s in streams if s["codec_type"] == "audio"), None)
            if not v or not a or (v["width"], v["height"]) != SIZE or v["codec_name"] != "h264":
                raise RuntimeError("MP4 nao passou no QA: audio/video/formato")
            tmp_out.replace(destination)
        finally:
            tmp_out.unlink(missing_ok=True)
    metadata = {"engine": "estudio-cpu-v1", "publish": False, "gpu": False,
                "paid_apis": False, "scenes": report, "output": str(destination)}
    destination.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/estudio_cpu.mp4"))
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--tts", choices=("none", "espeak"), default="none")
    args = parser.parse_args()
    spec_file = args.spec.resolve()
    spec = validate(json.loads(spec_file.read_text(encoding="utf-8")), spec_file.parent)
    if args.check_only:
        print("ROTEIRO VALIDO", len(spec["scenes"]), "cenas; zero chamadas pagas")
        return
    result = render(spec, spec_file.parent, args.output.resolve(), args.tts)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

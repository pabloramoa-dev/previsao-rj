"""Renderiza alertas reais no próprio estúdio HyperFrames do @previsaorj."""
import json
from pathlib import Path
from tools.alerta_14h import validar
from tools.alerta_14h_roteiro import batidas, texto_para_arquivo

def main():
    rel = validar(json.loads(Path("output/alertas/consulta.json").read_text(encoding="utf-8")))
    out = Path("output/alertas/ALERTA.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    texto_para_arquivo(rel, out.parent / "LEGENDA.txt")
    snapshot = json.loads(Path("output/alertas/snapshot.json").read_text(encoding="utf-8"))
    from src.previsao_rj.editorial import formats
    from hyperframes import gerar_hf
    beats = batidas(rel)
    # Reaproveita cena, personagens, TTS e render do canal sem contaminar
    # outros vídeos; o override só existe neste processo de plantão.
    original = formats.prepare
    try:
        formats.prepare = lambda snap, formato, topic=None: {"beats": beats}
        pacote, b, segs, work = gerar_hf.preparar(
            "bia", out, snapshot, "rio_antes_de_sair")
    finally:
        formats.prepare = original
    gerar_hf.renderizar(out, pacote)
    gerar_hf.entregar("bia", out, pacote, b, segs, work)
    if not out.is_file() or out.stat().st_size < 100000:
        raise RuntimeError("MP4 não foi gerado corretamente")
    print("Plantão RJ:", out)

if __name__ == "__main__":
    main()

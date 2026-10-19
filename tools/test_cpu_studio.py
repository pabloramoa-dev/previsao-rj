"""Testes locais, sem GPU, rede ou publicacao."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cpu_studio", root / "tools" / "cpu_studio.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class EstudioCPUTest(unittest.TestCase):
    def setUp(self):
        self.path = root / "examples" / "cpu_piloto.json"
        self.base = json.loads(self.path.read_text(encoding="utf-8"))

    def test_roteiro_original_valido(self):
        self.assertIs(mod.validate(self.base, self.path.parent), self.base)

    def test_rejeita_formato_errado(self):
        case = dict(self.base, style="CUDA")
        with self.assertRaises(ValueError):
            mod.validate(case, self.path.parent)

    def test_rejeita_duracao_perigosa(self):
        case = json.loads(json.dumps(self.base))
        case["scenes"][0]["seconds"] = 999
        with self.assertRaises(ValueError):
            mod.validate(case, self.path.parent)

    def test_rejeita_arquivos_inexistentes(self):
        case = json.loads(json.dumps(self.base))
        case["scenes"][0]["voice_file"] = "audio-nao-existe.wav"
        with self.assertRaises(ValueError):
            mod.validate(case, self.path.parent)

    def test_video_pede_origem_de_uso(self):
        case = json.loads(json.dumps(self.base))
        case["scenes"][0]["video"] = "video.mp4"
        with self.assertRaises(ValueError):
            mod.validate(case, self.path.parent)

    def test_nao_permite_imagem_e_video_juntos(self):
        case = json.loads(json.dumps(self.base))
        case["scenes"][0]["video"] = "video.mp4"
        case["scenes"][0]["image"] = "arte.png"
        case["scenes"][0]["media_credit"] = "teste"
        with self.assertRaises(ValueError):
            mod.validate(case, self.path.parent)

    def test_renderiza_arte_sem_rede(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            mod.make_frame(self.base, self.base["scenes"][0], 0, path, self.path.parent)
            from PIL import Image
            with Image.open(path) as im:
                self.assertEqual(im.size, (1080, 1920))

if __name__ == "__main__":
    unittest.main()

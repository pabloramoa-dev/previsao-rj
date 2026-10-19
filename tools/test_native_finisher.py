"""Regressão do acabamento nativo: nunca troca o personagem nem gera TTS."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from tools import native_video_finisher as N

class NativeTests(unittest.TestCase):
    def test_sem_interatividade_preserva_video(self):
        with mock.patch.object(N, "finish", side_effect=AssertionError("nao deve chamar")):
            self.assertFalse(N.apply_from_metadata("inexistente.mp4", {}, Path.cwd())["applied"])

    def test_exige_origem_broll(self):
        with self.assertRaises(ValueError):
            N.validate({"pergunta":"Voce descobriu a pista?", "broll_video":"media.mp4"}, Path.cwd())

    def test_exige_quiz_com_opcoes(self):
        with self.assertRaises(ValueError):
            N.validate({"modo":"quiz","pergunta":"Qual e a resposta correta?"}, Path.cwd())

    def test_rejeita_caminho_fora_do_repo(self):
        with self.assertRaises(ValueError):
            N.validate({"pergunta":"O que vai acontecer a seguir?", "broll_video":"../../etc/passwd", "credito":"teste"}, Path.cwd())

    @unittest.skipUnless(os.environ.get("NATIVE_TEST_VIDEO")=="1", "video integrado roda na CI com ffmpeg")
    def test_gera_mp4_usando_audio_original(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            clip=root/"personagem.mp4"
            subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc2=size=540x960:rate=25",
                            "-f","lavfi","-i","sine=frequency=440:sample_rate=48000",
                            "-t","3.5","-c:v","libx264","-preset","ultrafast","-crf","28",
                            "-c:a","aac","-pix_fmt","yuv420p",str(clip)],check=True)
            info1=N._probe(clip)
            report=N.finish(clip,{"modo":"quiz","pergunta":"Qual das alternativas voce escolheria?",
                                  "opcoes":["Opcao numero um","Opcao numero dois"],"segundos":2.5},root)
            info2=N._probe(clip)
            self.assertTrue(report["applied"])
            self.assertEqual(info2["width"], info1["width"])
            self.assertGreater(info2["duration"], info1["duration"]+2)
            self.assertTrue(N.apply_from_metadata(clip, {"interatividade":{
                "modo":"quiz","pergunta":"Qual das alternativas voce escolheria?",
                "opcoes":["Opcao numero um","Opcao numero dois"],"segundos":2.5}},root)["reused"])
            shot=root/"ultimo.png"
            subprocess.run(["ffmpeg","-y","-v","error","-sseof","-0.8","-i",str(clip),"-frames:v","1",str(shot)],check=True)
            self.assertGreater(shot.stat().st_size,10000)

if __name__=="__main__":
    unittest.main()

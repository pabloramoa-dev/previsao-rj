import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("montar.py")
spec = importlib.util.spec_from_file_location("opuscar_rj_montar", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def snapshot():
    return {
        "source": "open-meteo",
        "generated_at": "2026-11-03T09:00:00-03:00",
        "forecast": {"today": {"locations": [
            {"name": "Copacabana", "min_c": 22, "max_c": 29, "rain_probability_pct": 35},
            {"name": "Niterói", "min_c": 21, "max_c": 28, "rain_probability_pct": 50},
            {"name": "Nova Iguaçu", "min_c": 20, "max_c": 32, "rain_probability_pct": 75},
            {"name": "Campo Grande", "min_c": 20, "max_c": 31, "rain_probability_pct": 60},
        ]}}
    }


class DadosReais(unittest.TestCase):
    def test_filtro_e_painel(self):
        dia, locais = mod.extrair_painel(snapshot())
        self.assertEqual(dia, "2026-11-03")
        self.assertEqual(len(locais), 4)
        self.assertEqual(locais[2]["chuva"], 75)
        self.assertEqual(locais[0]["nome"], "Copacabana")

    def test_nao_publicar_fixture(self):
        payload = snapshot()
        payload["source"] = "fixture_technical_test"
        with self.assertRaises(ValueError):
            mod.extrair_painel(payload)

    def test_descarta_valores_falsos(self):
        payload = snapshot()
        payload["forecast"]["today"]["locations"][0]["rain_probability_pct"] = 101
        _, locais = mod.extrair_painel(payload)
        self.assertNotIn("Copacabana", [p["nome"] for p in locais])

    def test_menos_de_duas_previsoes_bloqueia(self):
        payload = snapshot()
        payload["forecast"]["today"]["locations"] = payload["forecast"]["today"]["locations"][:1]
        with self.assertRaises(ValueError):
            mod.extrair_painel(payload)


if __name__ == "__main__":
    unittest.main()

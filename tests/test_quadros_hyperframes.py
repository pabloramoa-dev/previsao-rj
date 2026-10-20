"""Regressão: o quadro detalhado precisa existir no compositor de produção."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hyperframes"))
from compor import cena_quadro

def test_quadros_hyperframes_usam_todos_os_indicadores():
    cidades = [dict(nome="Niterói", min=21, max=29, prob_chuva=65, chuva_mm=2.5, vento_kmh=33),
               dict(nome="Baixada", min=22, max=31)]
    p = dict(ceu="sol", dur=10)
    c = dict(id="quadro", tipo="quadro", ini=0, batidas=[0])
    b = [dict(dados=dict(cidades=cidades, titulo="HOJE NA REGIÃO"))]
    html = cena_quadro(p, c, b)
    for value in ("NITERÓI", "BAIXADA", "21°", "29°", "65%", "2,5 mm", "33 km/h", "CHUVA", "VOLUME", "RAJADAS"):
        assert value in html
    assert html.count("—") == 3
    assert "None" not in html and "nan" not in html

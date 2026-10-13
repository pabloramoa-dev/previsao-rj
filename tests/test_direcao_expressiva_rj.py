"""Direção expressiva do RJ, sem rede, API de imagem nem Manim."""
import copy
import json
import math
from pathlib import Path

from src.previsao_rj.render.characters import director as D
from src.previsao_rj.render.characters import quality_direction as Q


def roteiro():
    batidas = [
        {"tipo": "abertura", "fala": "Bom dia Rio! Vamos ver o tempo.", "legenda": "BOM DIA RIO", "dados": {}},
        {"tipo": "numero", "fala": "Faz trinta graus no Rio.", "legenda": "30° NO RIO", "dados": {"numero": "30°"}},
        {"tipo": "quadro", "fala": "Niterói tem previsão diferente.", "legenda": "NITERÓI", "dados": {"cidades": ["Rio", "Niterói"]}},
        {"tipo": "alerta", "fala": "Atenção à chuva.", "legenda": "CHUVA", "dados": {"cor": "alerta"}},
        {"tipo": "cta", "fala": "Segue o perfil.", "legenda": "SIGA", "dados": {}},
    ]
    segs = [dict(ini=3.0*i, fim=3.0*(i+1)) for i in range(len(batidas))]
    return batidas, segs


def test_direcao_nao_altera_numeros_nem_roteiros():
    b, s = roteiro()
    old = copy.deepcopy(b)
    for personagem in ("bira", "bia"):
        plano = D.planejar(b, s, personagem)
        assert b == old
        assert plano == D.planejar(b, s, personagem)
        assert [x["gesto"] for x in plano] == ["enfatizar","enfatizar","apontar","alertar","acolher"]
        assert [x["camera"] for x in plano] == ["aproximar","aproximar","abrir","aproximar","estabilizar"]
        assert len({x["gesto"] for x in plano}) >= 4


def test_configuracao_e_limites():
    from unittest.mock import patch
    with patch.dict("os.environ", {"PREVISAO_RJ_DIRECAO": "0"}):
        assert D.ativo() is False
    with patch.dict("os.environ", {"PREVISAO_RJ_DIRECAO": "1"}):
        assert D.ativo() is True
    assert all(0 <= abs(x) <= 16 for x in D.ANGULOS.values())
    assert all(1.0 <= x <= 1.06 for x in D.CAMERAS.values())


def test_falas_ruins_sao_rejeitadas():
    b, s = roteiro()
    import pytest
    with pytest.raises(ValueError):
        D.planejar(b, s[:-1], "bira")
    s[2]["ini"] = 5.0
    with pytest.raises(ValueError):
        D.planejar(b, s, "bia")


def test_gestos_manim_suaves():
    for gesture in D.GESTOS:
        assert D.deslocamento(gesture, 0, 0, 3) == (0.0, 0.0)
        assert D.deslocamento(gesture, 3, 0, 3) == (0.0, 0.0)
        for t in (.1, .5, 1.5, 2.9):
            assert all(math.isfinite(y) and abs(y) <= .23 for y in D.deslocamento(gesture,t,0,3))


def test_qa_estrutura_e_audio(tmp_path):
    b, s = roteiro()
    plano = D.planejar(b, s, "bira")
    pacote = {"personagem":"bira","batidas":[dict(v, ini=t["ini"],fim=t["fim"]) for v,t in zip(b,s)],
              "direcao": plano,"cidades":[{"nome":"Rio de Janeiro"}]}
    probe = {"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}
    rel = Q.verificar(pacote,probe)
    assert rel["aprovado_tecnicamente"]
    assert rel["camera_adaptativa"]
    path = tmp_path/"quality.json"
    Q.salvar(path,rel)
    assert json.loads(path.read_text())["aprovado_tecnicamente"]
    assert Q.verificar(pacote,{"streams":[{"codec_type":"video"}]})["erros"]


def test_html_preserva_dados_e_camada_principal():
    pytest = __import__("pytest")
    pytest.importorskip("numpy")
    from test_hyperframes_estudio import pacote
    from hyperframes.compor import compor
    p = pacote()
    times = [dict(ini=b["ini"],fim=b["fim"]) for b in p["batidas"]]
    p["direcao"] = D.planejar(p["batidas"],times,"bira")
    html = compor(p)
    assert "data-ombro-e" in html and 'id="ap-bracoE"' in html
    assert 'id="ap-bracoD"' in html and 'id="ap-wrap"' in html
    assert 'D.direcao[k]' in html
    for cidade in p["cidades"]:
        assert cidade["nome"].upper() in html

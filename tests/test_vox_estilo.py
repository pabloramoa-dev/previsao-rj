"""Chave do estilo colagem (vox) e as contas puras da camada de papel."""
import pytest

from src.previsao_rj.render.characters.pipeline import estilo_vox


def test_vox_e_o_padrao(monkeypatch):
    monkeypatch.delenv('PREVISAO_RJ_ESTILO', raising=False)
    assert estilo_vox() is True


@pytest.mark.parametrize('valor, esperado', [
    ('vox', True), ('', True), ('classico', False), (' Classico ', False),
])
def test_chave_de_estilo(monkeypatch, valor, esperado):
    monkeypatch.setenv('PREVISAO_RJ_ESTILO', valor)
    assert estilo_vox() is esperado


def test_ganho_fixo_e_degraus():
    VX = pytest.importorskip('src.previsao_rj.render.characters.vox_papel',
                             reason='manim não instalado no CI de testes')
    assert VX.ganho_para(-20.5) == pytest.approx(4.0)
    assert VX.ganho_para(-60.0) == 18.0          # teto de segurança
    assert VX.ganho_para(None) == 0.0            # sem medição, não mexe
    passos = {round(VX.degrau(t / 100), 4) for t in range(0, 36)}
    assert len(passos) <= 5                      # 12 fps em 0,36 s: degraus, não rampa
    assert VX.degrau(0.36) == 1.0 and VX.degrau(5) == 1.0

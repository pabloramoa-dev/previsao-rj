"""Isolamento em relacao ao pipeline anterior — Plano Mestre, secoes 3.1 e 17.2."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
import isolation_guard  # noqa: E402


def test_nenhum_identificador_da_conta_antiga_no_projeto():
    assert isolation_guard.scan() == []


def test_o_guard_cobre_codigo_config_workflows_scripts_e_testes():
    roots = {str(r) for r in isolation_guard.ROOTS}
    assert roots == {"src", ".github", "config", "scripts", "tests"}


def test_nenhum_import_em_runtime_do_projeto_anterior():
    for path in Path("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import previsao_lib" not in text
        assert "from previsao_lib" not in text

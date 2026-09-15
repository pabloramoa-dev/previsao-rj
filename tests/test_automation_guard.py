"""As travas da automação diária, presas em teste.

Até 15/09/2026 este arquivo cobrava que o `schedule` do Reel da manhã
estivesse COMENTADO — era o gate de produção enquanto não havia Reel real
aprovado. O primeiro Reel foi publicado em 13/09 e a automação passou a existir
de verdade, então o que precisa ser garantido mudou: agora o agendamento está
ligado e quem segura a publicação é a chave `AUTOMATION_ENABLED` mais a trava
de idempotência do dia.
"""
from pathlib import Path

import yaml

MANHA = Path('.github/workflows/reel_manha.yml')
MANUAL = Path('.github/workflows/publicar_manual.yml')


def carregar(caminho: Path) -> dict:
    return yaml.safe_load(caminho.read_text(encoding='utf-8'))


def test_chave_geral_da_automacao_existe():
    """Sem a variable AUTOMATION_ENABLED = 'true', o job inteiro não roda.
    É o rollback de um clique, sem editar arquivo."""
    texto = MANHA.read_text(encoding='utf-8')
    assert "AUTOMATION_ENABLED == 'true'" in texto
    jobs = carregar(MANHA)['jobs']
    # O gate fica no primeiro job da cadeia; o resto depende dele.
    assert jobs['trava']['if'] == "vars.AUTOMATION_ENABLED == 'true'"
    assert jobs['reel']['needs'] == 'trava'


def test_reel_diario_tem_mais_de_uma_tentativa_de_cron():
    """O cron do GitHub atrasa e às vezes engole a execução. Uma tentativa só
    significa, num dia ruim, previsão da manhã publicada à tarde."""
    agenda = carregar(MANHA)[True]['schedule']
    assert len(agenda) >= 2
    horas = {int(item['cron'].split()[1]) for item in agenda}
    # Todas as tentativas antes das 6h de Brasília (UTC-3), ou seja, antes das 9 UTC.
    assert horas and max(horas) < 9


def test_reel_diario_trava_segunda_publicacao_no_mesmo_dia():
    """Várias tentativas de cron só são seguras com a trava do dia, e ela é
    conferida DUAS vezes: antes de instalar qualquer coisa (job `trava`) e
    depois do scan, com a fila já atualizada (`--exigir-inedito-hoje`)."""
    texto = MANHA.read_text(encoding='utf-8')
    assert '--exigir-inedito-hoje' in texto
    assert carregar(MANHA)['jobs']['reel']['if'] == "needs.trava.outputs.pular != 'sim'"


def test_publicadores_compartilham_a_mesma_concorrencia():
    """Diário e manual publicam na mesma conta: nunca os dois ao mesmo tempo."""
    grupo = carregar(MANHA)['concurrency']['group']
    assert grupo == carregar(MANUAL)['concurrency']['group']
    assert carregar(MANHA)['concurrency']['cancel-in-progress'] is False


def test_manual_nao_tem_mais_agendamento():
    """O agendamento de uma vez só (07:07 de 13/09/2026) já cumpriu o papel —
    e nem chegou a disparar. Quem publica todo dia é o reel_manha."""
    gatilhos = carregar(MANUAL)[True]
    assert 'schedule' not in gatilhos
    assert 'workflow_dispatch' in gatilhos


def test_fixture_nunca_publica():
    texto = MANUAL.read_text(encoding='utf-8')
    assert 'PUBLICAÇÃO BLOQUEADA: dados de fixture nunca vão para o feed.' in texto


def test_os_dois_publicadores_amarram_a_pauta_escolhida():
    """Render, legenda e fila têm de sair do mesmo item — foi o desencontro do
    primeiro Reel real, em que a fila registrou pauta diferente da que foi ao ar."""
    for caminho in (MANHA, MANUAL):
        texto = caminho.read_text(encoding='utf-8')
        assert 'scripts.escolher_pauta' in texto
        assert '--format "${{ steps.pauta.outputs.formato }}"' in texto
        assert '--pauta output/pauta.json' in texto
        assert '--dedupe-key "${{ steps.pauta.outputs.dedupe_key }}"' in texto

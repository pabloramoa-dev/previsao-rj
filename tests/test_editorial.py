import json
from pathlib import Path
from src.previsao_rj.editorial.scoring import score_snapshot
from src.previsao_rj.editorial.script import build_script

def fixture():
    return json.loads(Path('tests/fixtures/snapshot_rj.json').read_text(encoding='utf-8'))

def test_score_is_deterministic():
    a=score_snapshot(fixture()); b=score_snapshot(fixture())
    assert a==b and a['total']>=14

def test_script_mentions_rj_brand_logic():
    s=build_script(fixture())
    assert 'Rio' in s['narration'] and 'Previsão RJ' in s['narration']

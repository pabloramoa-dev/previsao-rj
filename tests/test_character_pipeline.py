from src.previsao_rj.render.characters.pipeline import PRESETS, FILTER, demo_beats, snapshot_beats
import json
from pathlib import Path


def test_original_voice_presets():
    assert PRESETS['ranzinza'] == dict(voice='pm_alex', pitch=.88, speed=.95, gap=.30)
    assert PRESETS['maria'] == dict(voice='pf_dora', pitch=.94, speed=.95, gap=.30)
    assert 'atempo=1.13636' in FILTER.format(pitch=.88, inv=1/.88)


def test_weather_script_matches_snapshot():
    snapshot = json.loads(Path('tests/fixtures/snapshot_rj.json').read_text())
    rows = [b for b in snapshot_beats(snapshot) if b['tipo'] == 'cidade']
    assert [b['dados']['cidade']['max'] for b in rows] == [29, 31, 35]
    assert len(demo_beats('maria')) == 4

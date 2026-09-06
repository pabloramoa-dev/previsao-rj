from pathlib import Path

def test_schedule_not_active_and_second_gate_present():
    t=Path('.github/workflows/reel_manha.yml').read_text(encoding='utf-8')
    assert '# schedule:' in t
    assert "AUTOMATION_ENABLED == 'true'" in t

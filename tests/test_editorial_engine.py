from copy import deepcopy
from datetime import timedelta
from src.previsao_rj.collectors.base import now
from src.previsao_rj.editorial.engine import evaluate, queue_file


def test_old_snapshot_blocks_all_candidates(snapshot):
    result = evaluate(snapshot, reference=now() + timedelta(hours=4))
    assert result and all('fonte_vencida_ou_timestamp_invalido' in c['vetoes'] for c in result)


def test_low_confidence_veto(snapshot):
    snapshot['confidence']['score'] = 20
    assert all(c['status'] == 'blocked' for c in evaluate(snapshot))


def test_wind_is_editorial_candidate(snapshot):
    locs = snapshot['forecast']['today']['locations']
    for l in locs: l.update(max_c=22, rain_probability_pct=80, wind_gust_max_kmh=25)
    locs[0]['wind_gust_max_kmh'] = 58
    assert any(c['topic'] == 'vento' and c['status'] == 'ready' for c in evaluate(snapshot))


def test_no_rain_reel_based_only_on_percentage(snapshot):
    for l in snapshot['forecast']['today']['locations']:
        l.update(max_c=22, rain_probability_pct=70, rain_window=None, wind_gust_max_kmh=20, beach=False)
    assert not any(c['topic'] in {'chuva', 'janela_chuva'} for c in evaluate(snapshot))


def test_queue_is_idempotent_and_preserves_published(snapshot, tmp_path):
    result = evaluate(snapshot)
    result[0].update(status='published')
    path = tmp_path/'queue.json'
    queue_file(path, result)
    again = queue_file(path, evaluate(snapshot))
    assert len(again) == len(result) and again[0]['status'] == 'published'


def test_repeat_hook_veto(snapshot):
    first = evaluate(snapshot)[0]
    first.update(status='published', published_at=now().isoformat())
    matching = next(c for c in evaluate(snapshot, [first]) if c['dedupe_key'] == first['dedupe_key'])
    assert 'duplicata' in matching['vetoes']

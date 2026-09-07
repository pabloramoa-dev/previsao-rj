from copy import deepcopy
from src.previsao_rj.normalizers import snapshot as snap
from src.previsao_rj.editorial.contrast import regional_contrast
from src.previsao_rj.quality.confidence import observation_match


def test_uv_uses_first_available_model_with_provenance(collected, tier1_locations):
    collected = deepcopy(collected)
    for model, result in collected.items():
        for raw in result.payload['points'].values():
            raw['daily']['uv_index_max'] = [8.2, 7.1] if model == 'gfs_seamless' else [None, None]
    d = snap.build(collected, tier1_locations)
    entry = d['forecast']['today']['locations'][0]
    assert entry['uv_index_max'] == 8.2
    assert entry['field_provenance']['uv_index_max']['model'] == 'gfs_seamless'
    assert entry['field_provenance']['uv_index_max']['fallback_used']
    assert d['fallback_used']


def test_missing_rain_remains_unknown_not_dry(collected, tier1_locations):
    collected = deepcopy(collected)
    for result in collected.values():
        for raw in result.payload['points'].values():
            raw['daily']['precipitation_probability_max'] = [None, None]
            raw['daily']['precipitation_sum'] = [None, None]
    entry = snap.build(collected, tier1_locations)['forecast']['today']['locations'][0]
    assert entry['rain_probability_pct'] is None
    assert entry['rain_mm'] is None


def test_secondary_different_date_never_fills_today(collected, tier1_locations):
    collected = deepcopy(collected)
    for model, result in collected.items():
        for raw in result.payload['points'].values():
            raw['daily']['uv_index_max'] = [9, 9] if model == 'gfs_seamless' else [None, None]
            if model == 'gfs_seamless': raw['daily']['time'] = ['2000-01-01', '2000-01-02']
    assert snap.build(collected, tier1_locations)['forecast']['today']['locations'][0]['uv_index_max'] is None


def test_wind_alone_can_create_regional_story():
    locations = [dict(id='a', name='Oeste', max_c=22, rain_probability_pct=80, wind_gust_max_kmh=58),
                 dict(id='b', name='Litoral', max_c=22, rain_probability_pct=82, wind_gust_max_kmh=25)]
    c = regional_contrast(locations)
    assert not c['temperature']['relevant'] and not c['rain']['relevant']
    assert c['gust']['spread'] == 33 and c['has_contrast']


def test_observation_without_matching_does_not_raise_confidence():
    assert observation_match('ok', None)[0] == 0

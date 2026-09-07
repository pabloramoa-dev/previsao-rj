from datetime import datetime, timedelta
from io import BytesIO
import xml.etree.ElementTree as ET
import pytest
from PIL import Image
import resvg_py
from src.previsao_rj.render.stories import svg_card, hourly_sample, generate, ASSETS


def test_story_renders_unicode_missing_data_and_escaped_names(snapshot):
    loc=dict(snapshot['forecast']['today']['locations'][0],name='D’Água & Região',uv_index_max=None,weather_code=None)
    svg=svg_card(snapshot,loc,preview=True)
    ET.fromstring(svg)
    assert 'D’Água &amp; Região' in svg and 'Condição indisponível' in svg
    png=resvg_py.svg_to_bytes(svg_string=svg,font_files=[str(ASSETS/'Manrope-Regular.ttf'),str(ASSETS/'Manrope-Bold.ttf')])
    assert Image.open(BytesIO(png)).size==(1080,1920)


def test_hourly_cards_only_use_future_times_on_target_day():
    generated=datetime.fromisoformat('2026-09-07T11:06:00-03:00')
    loc={'hourly':[{'time':f'2026-09-07T{h:02d}:00:00-03:00','temperature_2m':h} for h in range(24)]}
    rows=hourly_sample(loc,generated,'2026-09-07')
    assert [r['temperature_2m'] for r in rows]==[12,15,18,21]


def test_production_story_rejects_expired_snapshot(snapshot,tmp_path):
    reference=datetime.fromisoformat(snapshot['generated_at'])+timedelta(hours=4)
    with pytest.raises(ValueError,match='vencido'):generate(snapshot,tmp_path,reference=reference)

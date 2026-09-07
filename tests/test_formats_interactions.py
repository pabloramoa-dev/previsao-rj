from copy import deepcopy
from datetime import timedelta
import hashlib,hmac,json
import pytest
from src.previsao_rj.collectors.base import now
from src.previsao_rj.editorial.formats import prepare
from src.previsao_rj.editorial.engine import evaluate
from src.previsao_rj.editorial.script import build_script
from src.previsao_rj.interactions.replies import prepare_reply
from src.previsao_rj.interactions.webhook import receive
from src.previsao_rj.normalizers.snapshot import hourly_rows, is_stale


def test_uniform_temperature_has_no_invented_contrast(snapshot):
    for loc in snapshot['forecast']['today']['locations']: loc['max_c']=22
    script=build_script(snapshot)
    assert 'DOIS RIOS' not in script['hook'] and 'dois ritmos' not in script['narration']


def test_format_refuses_stale(snapshot):
    with pytest.raises(ValueError): prepare(snapshot,reference=now()+timedelta(hours=4))


def test_missing_beach_report_blocks_format(snapshot):
    with pytest.raises(ValueError):prepare(snapshot,'vai_dar_praia')


def test_only_one_weekend_day_does_not_claim_full_weekend(snapshot):
    snapshot['forecast']['today']['date']='2026-09-06'
    snapshot['forecast']['tomorrow']['date']='2026-09-07'
    assert not any(c['format']=='fim_de_semana' for c in evaluate(snapshot))


def test_invalid_timestamp_blocks_without_crashing(snapshot):
    snapshot['generated_at']='invalid'
    assert all(c['status']=='blocked' for c in evaluate(snapshot))


def test_cache_age_cannot_be_reset_by_new_snapshot(snapshot):
    for s in snapshot['sources']: s['age_minutes']=180
    assert is_stale(snapshot)


def test_hourly_fallback_aligns_timestamp():
    data={'a':{'hourly':{'time':['2026-09-07T12:00'],'temperature_2m':[None]}},
          'b':{'hourly':{'time':['2026-09-07T11:00','2026-09-07T12:00'],'temperature_2m':[99,25]}}}
    rows=hourly_rows(data,['a','b'],'2026-09-07')
    assert rows[-1]['temperature_2m']==25 and rows[-1]['field_models']['temperature_2m']=='b'


def test_ambiguous_dm_does_not_invent_location(snapshot):
    reply=prepare_reply('Centro',snapshot)
    assert reply['status']=='clarification'


def test_webhook_signature_account_and_dedup(snapshot,tmp_path):
    body=json.dumps({'object':'instagram','entry':[{'id':'rj-test','messaging':[{'message':{'mid':'message-1','text':'Centro'}}]}]}).encode()
    signature='sha256='+hmac.new(b'test-secret',body,hashlib.sha256).hexdigest()
    db=tmp_path/'events.sqlite'
    with pytest.raises(ValueError): receive(body,'invalid','test-secret','rj-test',snapshot,db)
    assert receive(body,signature,'test-secret','different-account',snapshot,db)==[]
    assert len(receive(body,signature,'test-secret','rj-test',snapshot,db))==1
    assert receive(body,signature,'test-secret','rj-test',snapshot,db)==[]


def test_two_day_weekend_script(snapshot):
    snapshot['forecast']['today']['date']='2026-09-12'
    snapshot['forecast']['tomorrow']['date']='2026-09-13'
    text=' '.join(b['fala'] for b in prepare(snapshot,'fim_de_semana')['beats'])
    assert 'sábado' in text and 'domingo' in text


def test_beach_requires_matching_date_and_official_report(snapshot):
    locs=snapshot['forecast']['today']['locations']
    for e in locs:e['beach']=False
    locs[0]['beach']=True;key=locs[0]['id']
    snapshot['marine']={'status':'ok','data':{'points':{key:{'date':snapshot['forecast']['today']['date'],'wave_height_max':1.2}}}}
    snapshot['beach_status']={'status':'ok','data':{'points':{key:{'source_url':'https://example.invalid/fixture','valid_until':(now()+timedelta(hours=4)).isoformat(),'classification':'imprópria'}}}}
    text=' '.join(b['fala'] for b in prepare(snapshot,'vai_dar_praia')['beats'])
    assert 'imprópria' in text and 'segurança' in text
    snapshot['marine']['data']['points'][key]['date']='2000-01-01'
    with pytest.raises(ValueError):prepare(snapshot,'vai_dar_praia')


def test_game_has_three_separate_weather_windows(snapshot):
    start=now().replace(minute=0,second=0,microsecond=0)+timedelta(hours=3)
    end=start+timedelta(hours=2)
    loc=snapshot['forecast']['today']['locations'][0]
    loc['hourly']=[{'time':(start+timedelta(hours=i)).isoformat(),'precipitation_probability':50+i} for i in range(-2,4)]
    snapshot['events']=[{'verified':True,'name':'Evento fictício de teste','source_url':'https://example.invalid/test','location_id':loc['id'],'start_at':start.isoformat(),'end_at':end.isoformat(),'expires_at':end.isoformat()}]
    text=' '.join(b['fala'] for b in prepare(snapshot,'vai_ao_jogo')['beats'])
    assert 'chegada' in text and 'evento' in text and 'saída' in text
    loc['hourly']=loc['hourly'][:2]
    with pytest.raises(ValueError):prepare(snapshot,'vai_ao_jogo')

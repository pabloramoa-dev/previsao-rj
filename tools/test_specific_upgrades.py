from pathlib import Path
import importlib.util,sys,tempfile,unittest,json
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

class ChannelRegressions(unittest.TestCase):
 def test_offline_images_follow_real_timeline(self):
  name='studio' if ROOT.name=='pablo-guru' else 'estudio' if ROOT.name=='sabio-e-feliz' else None
  if not name:self.skipTest('Scene planner unchanged in this channel')
  VI=__import__(name+'.visual_images',fromlist=['preparar'])
  ep={'titulo':'Uma carta para a família','batidas':[{'fala':'A mãe abriu a carta em casa.'} for _ in range(5)]}
  segs=[{'ini':i*3,'fim':(i+1)*3} for i in range(5)]
  with tempfile.TemporaryDirectory() as d:
   mapping,report=VI.preparar(ep,segs,Path(d)/'assets',Path(d))
   self.assertEqual(len(mapping),5);self.assertEqual(report['ready'],5)
   self.assertTrue(all(s['status']=='local_fallback' for s in report['scenes']))
   self.assertTrue(all((Path(d)/'assets'/v).is_file() for v in mapping.values()))
 def test_weather_tips_do_not_invent_missing_values(self):
  if ROOT.name!='previsao-rj':self.skipTest('RJ advice only')
  from src.previsao_rj.render.practical import tips
  self.assertEqual(tips([{}]),[])
  self.assertEqual(tips([{'rain_probability_pct':80,'uv_index_max':9}]),['LEVE GUARDA-CHUVA','UV ALTO: PROTETOR E SOMBRA'])
 def test_stale_forecast_and_missing_weather_are_rejected(self):
  if ROOT.name!='previsao-sul-fluminense':self.skipTest('Sulflu freshness only')
  from src.forecast_quality import assess
  now=datetime.now(timezone.utc)
  data={'gerado_em':now.isoformat(),'cidades':[{'min':20,'max':30,'chuva_mm':2}]}
  r=assess(data,now);self.assertEqual(r['parts']['observation_match'],0)
  self.assertIn('so um modelo',r['notes'][0])
  with self.assertRaises(ValueError):assess({**data,'gerado_em':(now-timedelta(hours=3)).isoformat()},now)
  with self.assertRaises(ValueError):assess({**data,'cidades':[{'min':20,'max':None,'chuva_mm':None}]},now)
 def test_uncertain_receipt_stays_blocked_without_stopping_other_reconciliation(self):
  if ROOT.name!='mengao-da-sala':self.skipTest('Mengão reconciliation only')
  from src.flamengo import reconciliar as R
  items=[{'chave':'old','status':'publicacao_pendente','container_id':'1'}, {'chave':'ok','status':'publicacao_pendente','container_id':'2'}]
  saved=[]
  with patch.object(R.estado,'ler',return_value={'itens':items}),patch.object(R.estado,'salvar',side_effect=saved.append),patch.object(R.publicar,'verificar_destino'),patch.object(R.publicar,'_cfg',return_value=('user','token','base','mengaodasala')),patch.object(R.publicar,'_req',side_effect=[{'status_code':'FINISHED'},{'status_code':'PUBLISHED'}]):
   result=R.reconciliar()
  self.assertEqual(items[0]['status'],'publicacao_pendente');self.assertEqual(result['confirmados'],1)
  self.assertEqual(len(result['pendentes']),1);self.assertEqual(saved[0]['chave'],'ok')

if __name__=='__main__':unittest.main()

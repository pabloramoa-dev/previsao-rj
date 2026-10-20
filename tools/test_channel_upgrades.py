import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import channel_ops as C

class ProductionReceiptTests(unittest.TestCase):
 def test_changed_script_code_and_video_each_reject_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'src').mkdir();code=r/'src/render.py';code.write_text('VERSION=1');v=r/'test.mp4';v.write_bytes(b'video')
   ep={'id':'example','texto':'Original'};C.record_render(v,ep,r)
   self.assertFalse(C.validate_render(v,ep,r).get('legacy',False))
   with self.assertRaises(ValueError):C.validate_render(v,{**ep,'texto':'Changed'},r)
   code.write_text('VERSION=2')
   with self.assertRaises(ValueError):C.validate_render(v,ep,r)
   code.write_text('VERSION=1');v.write_bytes(b'changed')
   with self.assertRaises(ValueError):C.validate_render(v,ep,r)
 def test_uncertain_send_never_retries_and_can_resume_confirmed_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   C.pending_send(d,'episode','container')
   with self.assertRaises(RuntimeError):C.resume_send(d,'episode',lambda c:None)
   with self.assertRaises(RuntimeError):C.pending_send(d,'episode','another-container')
   self.assertEqual(C.resume_send(d,'episode',lambda c:'confirmed-media'),'confirmed-media')
   self.assertEqual(C.resume_send(d,'episode',lambda c:None),'confirmed-media')
 def test_approval_bookkeeping_keeps_editorial_signature(self):
  self.assertEqual(C.editorial_signature({'texto':'same','status':'rascunho'}),C.editorial_signature({'texto':'same','status':'aprovado','sha256':'123'}))
 def test_missing_metrics_are_not_zero(self):
  self.assertIsNone(C.normalize_metrics({'data':[]})['shares_per_1000_reached'])
  self.assertEqual(C.normalize_metrics({'data':[{'name':'reach','values':[{'value':100}]},{'name':'shares','values':[{'value':2}]}]})['shares_per_1000_reached'],20)
 def test_measurements_use_actual_media_and_do_not_repeat_window(self):
  now=datetime(2026,10,20,tzinfo=timezone.utc)
  def api(base,endpoint,token,params):
   if endpoint=='account':return {'username':'canal'}
   if endpoint=='account/media':return {'data':[{'id':'confirmed','timestamp':(now-timedelta(hours=30)).isoformat()}]}
   return {'data':[{'name':'reach','values':[{'value':100}]}]}
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'IG_USER_ID':'account','IG_ACCESS_TOKEN':'not-a-real-token'}):
   first=C.collect(d,'canal',api,now);second=C.collect(d,'canal',api,now)
   self.assertEqual(len(first['measurements']),1);self.assertEqual(len(second['measurements']),1)
   with self.assertRaises(ValueError):C.collect(d,'other-account',api,now)

if __name__=='__main__':unittest.main()

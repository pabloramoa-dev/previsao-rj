"""Browser regression: accept a clean frame and reject an image/caption collision."""
from pathlib import Path
import tempfile,subprocess
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
 work=Path(d)
 for broken in (False,True):
  work.joinpath('index.html').write_text('''<!doctype html><html><body style="margin:0"><div data-composition-id="test" data-width="1080" data-height="1920"><div class="clip panel" data-template="story_frame_image" data-start="0" data-duration="3"><h1 style="position:absolute;top:20px">Title</h1><div class="art"><img style="position:absolute;left:200px;top:200px;width:400px;height:400px" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='blue'/%3E%3C/svg%3E"></div></div><div class="clip caps" data-start="0" data-duration="3" style="position:absolute;left:200px;top:TOPpx;width:400px;height:100px">Spoken caption</div></div><script>window.__timelines={test:{seek(){}}};</script></body></html>'''.replace('TOP','400' if broken else '900'))
  result=subprocess.run(['node',str(ROOT/'video/validate-production-layout.mjs'),str(work)],capture_output=True,text=True)
  if (result.returncode!=0)!=broken:
   raise AssertionError(result.stdout+result.stderr)
print('Browser checker accepts clean layout and rejects overlapping image/caption')

import json,sys
from pathlib import Path
from src.previsao_rj.publish.caption import build_caption
src=Path(sys.argv[1]); out=Path(sys.argv[2])
s=json.loads(src.read_text(encoding='utf-8'))
out.write_text(build_caption(s),encoding='utf-8')
print(out)

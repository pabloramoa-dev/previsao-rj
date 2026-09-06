from __future__ import annotations
import json, sys
from pathlib import Path
import yaml
from src.previsao_rj.collectors.open_meteo import fetch_point
from src.previsao_rj.normalizers.snapshot import build_snapshot

cfg=yaml.safe_load(Path('config/locations.yml').read_text(encoding='utf-8'))
# Piloto enxuto: contraste litoral / interior / Grande Tijuca.
ids={'copacabana','tijuca','nova_iguacu'}
locs=[x for x in cfg['locations'] if x['id'] in ids]
raw=[]
for loc in locs:
    raw.append(fetch_point(loc['latitude'],loc['longitude']))
snap=build_snapshot(locs,raw)
snap['forecast']['today']['confidence']=80
out=Path(sys.argv[1] if len(sys.argv)>1 else 'output/snapshot_live.json')
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)

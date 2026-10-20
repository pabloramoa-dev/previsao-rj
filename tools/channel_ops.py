"""Shared production receipts and read-only 24h/72h Instagram measurements.
No publishing, deletion, inferred results or credentials in reports.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import urllib.parse
import urllib.request

VERSION = 'cross-channel-2026-10-20-v1'
CODE_DIRS = ('motor','studio','daily','audio','estudio','hyperframes','src','video','tools')

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def engine_signature(root):
    root = Path(root)
    h = hashlib.sha256()
    for folder in CODE_DIRS:
        base = root/folder
        for p in sorted(base.rglob('*')) if base.exists() else []:
            rel = p.relative_to(root)
            if not p.is_file() or p.suffix not in {'.py','.mjs','.css','.json'}:
                continue
            if any(x in {'node_modules','__pycache__','build','assets','output','saida'} for x in rel.parts):
                continue
            if p.suffix == '.json' and p.name not in {'visual_images.json','package.json'}:
                continue
            if p.name.startswith('test') or p.name in {'channel_ops.py'}:
                continue
            h.update(str(rel).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def editorial_signature(editorial):
    # Publication/approval bookkeeping must not invalidate a spoken script.
    ignored = {'status','arquivo','sha256','aprovado_por','aprovado_em','publicado_em',
               'instagram_media_id','duracao_s','renderizador','render_receipt'}
    clean = {k:v for k,v in editorial.items() if k not in ignored}
    return hashlib.sha256(json.dumps(clean,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def record_render(video, editorial, root):
    receipt = {'version': VERSION, 'engine_sha256':engine_signature(root),
               'editorial_sha256': editorial_signature(editorial), 'video_sha256':digest(video),
               'created_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(Path(video).with_suffix('.production.json'),receipt)
    return receipt


def validate_render(video, editorial, root):
    p = Path(video).with_suffix('.production.json')
    if not p.exists():
        # Existing approved backlog keeps its own approval/hash protections.
        return {'legacy':True}
    receipt = json.loads(p.read_text())
    if receipt['video_sha256'] != digest(video):
        raise ValueError('Vídeo alterado após produção; renderizar novamente')
    if receipt['editorial_sha256'] != editorial_signature(editorial):
        raise ValueError('Roteiro alterado após produção; renderizar novamente')
    if receipt['engine_sha256'] != engine_signature(root):
        raise ValueError('Motor alterado após produção; renderizar novamente')
    return receipt


def _request(base, endpoint, token, params):
    # Secrets are sent in the header, never in logged URLs or exception bodies.
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f'{base}/{endpoint}?{query}',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=45) as response:
        return json.load(response)


def normalize_metrics(payload):
    values = {}
    for row in payload.get('data',[]):
        series = row.get('values') or []
        val = series[-1].get('value') if series else (row.get('total_value') or {}).get('value')
        if isinstance(val,(int,float)) and not isinstance(val,bool):
            values[row['name']] = val
    reach, shares = values.get('reach'), values.get('shares')
    values['shares_per_1000_reached'] = round(shares/reach*1000,2) if reach and shares is not None else None
    return values


def collect(root, expected, request=_request, now=None):
    root = Path(root); now = now or datetime.now(timezone.utc)
    token = os.environ.get('IG_ACCESS_TOKEN') or os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    user = os.environ.get('IG_USER_ID') or os.environ.get('INSTAGRAM_USER_ID')
    user = user or 'me'
    if not token:
        return {'status':'credentials_missing','measurements':[]}
    base = os.environ.get('IG_GRAPH_BASE','https://graph.instagram.com/v26.0').rstrip('/')
    account = request(base,user,token,{'fields':'id,username'})
    if (account.get('username') or '').lower().lstrip('@') != expected.lower().lstrip('@'):
        raise ValueError('Conta de métricas não corresponde a este canal')
    path=root/'data/channel_metrics.json'
    report=json.loads(path.read_text()) if path.exists() else {'measurements':[]}
    known={(x['media_id'],x['window']) for x in report['measurements']}
    # Discover confirmed media directly from Instagram; workflow success is irrelevant.
    media=request(base,user+'/media',token,{'fields':'id,timestamp,media_type','limit':100}).get('data',[])
    errors=[]
    for item in media:
        try:
            created=datetime.fromisoformat(item['timestamp'].replace('Z','+00:00'))
            age=(now-created).total_seconds()/3600
        except (ValueError,KeyError):
            continue
        window='24h' if 24<=age<72 else '72h' if 72<=age<168 else None
        if not window or (item['id'],window) in known:
            continue
        try:
            raw=request(base,item['id']+'/insights',token,{'metric':'reach,shares,saved,likes,comments'})
            metrics=normalize_metrics(raw)
            report['measurements'].append({'media_id':item['id'],'window':window,'age_hours':round(age,2),
                'collected_at':now.isoformat(),'metrics':metrics})
        except Exception as exc:
            errors.append({'media_id':item['id'],'error':type(exc).__name__})
    report.update(status='partial' if errors else 'ok',errors=errors,updated_at=now.isoformat(),account=expected)
    atomic_json(path,report)
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--account',required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=collect(root,args.account)
    # Summary contains counts and status only; never access tokens or raw API errors.
    print(json.dumps({'status':result['status'],'measurements':len(result['measurements'])}))
    if result['status']=='credentials_missing':
        print('::warning::Métricas não coletadas: credenciais deste repositório indisponíveis.')
    if result.get('errors'):
        print('::warning::Algumas métricas indisponíveis; valores ausentes não foram convertidos em zero.')



def send_receipts(root):
    path=Path(root)/'conteudo/send_receipts.json'
    return path, json.loads(path.read_text()) if path.exists() else {}


def resume_send(root, key, reconcile):
    _,items=send_receipts(root);old=items.get(key)
    if not old:return None
    if old.get('media_id'):return old['media_id']
    media=reconcile(old['container_id'])
    if not media:
        raise RuntimeError('Envio anterior inconclusivo: conteúdo mantido bloqueado, sem reenvio')
    confirm_send(root,key,media)
    return media


def pending_send(root, key, container):
    path,items=send_receipts(root)
    old=items.get(key)
    if old:
        raise RuntimeError('Recibo já existe; reconciliar antes de enviar')
    items[key]={'container_id':container,'status':'unknown','created_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(path,items)


def confirm_send(root, key, media):
    if not media:raise ValueError('Confirmação exige media_id')
    path,items=send_receipts(root)
    items[key]={**items.get(key,{}),'status':'published','media_id':media}
    atomic_json(path,items)


if __name__=='__main__':
    main()

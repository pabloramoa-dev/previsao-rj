"""Verificação e deduplicação de eventos; nenhuma chamada de envio à Meta."""
import hashlib
import hmac
import json
import sqlite3
from .replies import prepare_reply


def verify_challenge(query, token):
    if token and query.get('hub.mode')=='subscribe' and hmac.compare_digest(query.get('hub.verify_token',''),token):
        return query.get('hub.challenge','')
    raise ValueError('Verificação recusada')


def receive(body: bytes, signature: str, app_secret: str, account_id: str, snapshot, db_path, reference=None):
    if not app_secret or not account_id: raise ValueError('Configuração exclusiva RJ ausente')
    expected = 'sha256='+hmac.new(app_secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature or ''): raise ValueError('Assinatura inválida')
    payload = json.loads(body)
    if payload.get('object')!='instagram': raise ValueError('Objeto não suportado')
    output=[]
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, draft TEXT NOT NULL)')
        for entry in payload.get('entry',[]):
            if str(entry.get('id'))!=str(account_id): continue
            for event in entry.get('messaging',[]):
                message=event.get('message',{})
                if message.get('is_echo') or not message.get('text') or not message.get('mid'): continue
                key=hashlib.sha256((str(account_id)+':'+str(message['mid'])).encode()).hexdigest()
                if db.execute('SELECT 1 FROM events WHERE id=?',(key,)).fetchone(): continue
                draft=prepare_reply(message['text'],snapshot,reference=reference)
                db.execute('INSERT INTO events VALUES (?,?)',(key,json.dumps(draft,ensure_ascii=False)))
                output.append(draft)
    return output

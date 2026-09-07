"""Candidatos explicáveis, vetos e fila determinística. Não publica."""
from __future__ import annotations
from datetime import datetime, timedelta
import hashlib
import math
import json
from pathlib import Path
from ..collectors.base import now
from ..normalizers.snapshot import is_stale
from .contrast import regional_contrast


def stamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp exige fuso horário')
    return dt


def classify(score):
    return 'reel_urgent' if score >= 23 else 'reel_priority' if score >= 19 else 'reel' if score >= 14 else 'story' if score >= 9 else 'skip'


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def candidates(snapshot, reference=None):
    reference = reference or now()
    block = snapshot['forecast']['today']
    locs = block['locations']
    c = regional_contrast(locs)
    result = []

    def add(format, topic, locations, utility, urgency, contrast, shareability, *, extra=None):
        facts = {k: v for e in locations for k, v in [(e['id'], {
            'max_c': e.get('max_c'), 'rain_probability_pct': e.get('rain_probability_pct'),
            'wind_gust_max_kmh': e.get('wind_gust_max_kmh')})]}
        result.append({'format': format, 'topic': topic, 'location_ids': [e['id'] for e in locations],
                       'facts': facts, 'parts': dict(utility=utility, urgency=urgency,
                        contrast=contrast, shareability=shareability), 'extra': extra or {}})

    valid = [e for e in locs if _number(e.get('min_c')) and _number(e.get('max_c'))]
    if valid:
        add('rio_antes_de_sair', 'resumo', valid, 3, 3, 3 if c['has_contrast'] else 0, 3)
    for metric, topic in [('temperature', 'temperatura'), ('rain', 'chuva'), ('gust', 'vento')]:
        item = c[metric]
        if item['relevant']:
            pair = [e for e in locs if e['id'] in {item['low']['id'], item['high']['id']}]
            high = item['high']['value']
            urgency = (5 if high >= 70 else 4 if high >= 45 else 2) if metric == 'gust' else (4 if high >= 35 else 2) if metric == 'temperature' else 3
            strength = 5 if item['spread'] >= item['threshold'] * 2 else 3
            add('chove_onde', topic, pair, 5, urgency, strength, 3, extra={'contrast': item})
    windows = [e for e in locs if e.get('rain_window') and _number(e.get('rain_mm')) and e['rain_mm'] >= 1]
    if windows and not c['rain']['relevant']:
        add('chove_onde', 'janela_chuva', windows, 4, 4, 0, 4)
    gusts = [e for e in locs if (e.get('wind_gust_max_kmh') or 0) >= 45]
    if gusts and not c['gust']['relevant']:
        add('rio_antes_de_sair', 'vento', gusts, 5, 4, 0, 4)
    beaches = [e for e in locs if e.get('beach')]
    if beaches:
        add('vai_dar_praia', 'praia', beaches, 4, 3, 3 if c['has_contrast'] else 0, 5)
    day_blocks = [b for b in snapshot['forecast'].values() if isinstance(b, dict) and b.get('date')]
    weekend = [b for b in day_blocks if stamp(b['date'] + 'T12:00:00-03:00').weekday() >= 5]
    if len({b['date'] for b in weekend}) >= 2:
        add('fim_de_semana', 'fim_de_semana', valid, 4, 3, 3 if c['has_contrast'] else 0, 5,
            extra={'dates': [b['date'] for b in weekend], 'forecast': {b['date']: [
                {k: e.get(k) for k in ('id','max_c','rain_probability_pct','wind_gust_max_kmh')}
                for e in b['locations']] for b in weekend}})
    for event in snapshot.get('events', []) + snapshot.get('football', []):
        try:
            active = event.get('verified') is True and event.get('source_url', '').startswith('https://') and (
                reference < stamp(event['expires_at']) and reference < stamp(event['end_at']) and
                stamp(event['start_at']) < reference + timedelta(hours=36))
        except (KeyError, ValueError, TypeError):
            active = False
        loc = next((e for e in locs if e['id'] == event.get('location_id')), None)
        if active and loc:
            add('vai_ao_jogo', 'evento', [loc], 5, 5, 2, 5, extra={'event': event})
    return result


def evaluate(snapshot, history=None, reference=None):
    reference = reference or now()
    history = [h for h in (history or []) if h.get('status') == 'published']
    valid_history = []
    for item in history:
        try:
            age = reference - stamp(item['published_at'])
            if timedelta(0) <= age < timedelta(days=7):
                valid_history.append(item)
        except (KeyError, ValueError, TypeError):
            continue
    history = sorted(valid_history, key=lambda h: h['published_at'])
    confidence = snapshot.get('confidence', {}).get('score',
                   snapshot['forecast']['today'].get('confidence', 0))
    try:
        stale = is_stale(snapshot, reference=reference)
    except (KeyError, ValueError, TypeError):
        stale = True
    evaluated = []
    for candidate in candidates(snapshot, reference):
        parts = candidate['parts']
        previous = next((h for h in reversed(history) if h.get('format') == candidate['format']
                         and h.get('topic') == candidate['topic']), None)
        parts['novelty'] = 5 if previous is None else 0 if previous.get('facts') == candidate['facts'] else 3
        candidate['total'] = sum(parts.values())
        candidate['classification'] = classify(candidate['total'])
        candidate['character'] = 'bia' if candidate['format'] in {'vai_dar_praia', 'fim_de_semana'} else 'bira'
        if len(history) >= 2 and all(h.get('character') == candidate['character'] for h in history[-2:]):
            candidate['character'] = 'bia' if candidate['character'] == 'bira' else 'bira'
        identity = json.dumps([candidate['format'], candidate['topic'], candidate['facts'],
                              candidate['extra']], sort_keys=True, ensure_ascii=False)
        candidate['hook_key'] = hashlib.sha256(identity.encode()).hexdigest()[:20]
        date = snapshot['forecast']['today'].get('date', snapshot['generated_at'][:10])
        candidate['dedupe_key'] = hashlib.sha256((date + candidate['hook_key']).encode()).hexdigest()
        candidate['created_at'] = reference.isoformat()
        try:
            source_expiry = stamp(snapshot['generated_at']) + timedelta(minutes=120)
        except (KeyError, ValueError, TypeError):
            source_expiry = reference
        candidate['expires_at'] = min(reference + timedelta(hours=2), source_expiry).isoformat()
        veto = []
        if stale: veto.append('fonte_vencida_ou_timestamp_invalido')
        if confidence < 35: veto.append('confianca_abaixo_de_35')
        if confidence < 50 and candidate['classification'].startswith('reel'):
            candidate['classification'] = 'story'
        if previous and previous.get('facts') == candidate['facts']:
            veto.append('sem_mudanca_material')
        for old in history:
            try:
                recent = reference - stamp(old['published_at']) < timedelta(days=7)
            except (KeyError, ValueError):
                continue
            if recent and old.get('hook_key') == candidate['hook_key']:
                veto.append('gancho_repetido_em_7_dias')
            if old.get('dedupe_key') == candidate['dedupe_key']:
                veto.append('duplicata')
            if reference - stamp(old['published_at']) < timedelta(hours=3) and old.get('classification') in {'reel_priority', 'reel_urgent'}:
                if candidate['topic'] == 'resumo': candidate['classification'] = 'story'
        if candidate['format'] == 'vai_dar_praia':
            if snapshot.get('marine', {}).get('status') not in {'ok', 'cached'}:
                veto.append('mar_indisponivel')
            if snapshot.get('beach_status', {}).get('status') not in {'ok', 'cached'}:
                veto.append('balneabilidade_oficial_indisponivel')
        if candidate['format'] == 'vai_ao_jogo':
            event = candidate['extra']['event']
            loc = next(e for e in snapshot['forecast']['today']['locations'] if e['id'] == event['location_id'])
            if not loc.get('hourly'): veto.append('previsao_horaria_do_evento_indisponivel')
        candidate['vetoes'] = sorted(set(veto))
        candidate['status'] = 'blocked' if veto else 'skipped' if candidate['classification'] == 'skip' else 'ready'
        candidate['confidence'] = confidence
        candidate['language'] = 'probabilistic' if confidence < 50 else 'forecast'
        evaluated.append(candidate)
    return sorted(evaluated, key=lambda c: (-c['total'], c['dedupe_key']))


def queue_file(path, candidates):
    """Fila local idempotente: nunca republica, preserva estados finalizados."""
    path = Path(path)
    previous = json.loads(path.read_text()) if path.exists() else []
    items = {c['dedupe_key']: c for c in previous}
    for item in items.values():
        if item.get('status') in {'ready', 'blocked', 'skipped'}:
            try:
                if stamp(item['expires_at']) <= now():
                    item['status'] = 'expired'
            except (KeyError, ValueError, TypeError):
                item['status'] = 'expired'
    for candidate in candidates:
        old = items.get(candidate['dedupe_key'], {})
        if old.get('status') not in {'published', 'publishing', 'unknown'}:
            items[candidate['dedupe_key']] = candidate
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(list(items.values()), ensure_ascii=False, indent=2))
    temporary.replace(path)
    return list(items.values())

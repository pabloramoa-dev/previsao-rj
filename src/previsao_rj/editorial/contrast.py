"""Contraste entre localidades sem converter campo ausente em zero."""
import math
from .. import config


def regional_contrast(locations):
    limits = config.load_thresholds()
    fields = {'temperature': ('max_c', limits.get('regional_temp_contrast_c', 4)),
              'rain': ('rain_probability_pct', 30),
              'gust': ('wind_gust_max_kmh', 15)}
    result = {}
    for key, (field, threshold) in fields.items():
        values = [(e, e.get(field)) for e in locations]
        values = [(e, float(v)) for e, v in values if isinstance(v, (int, float)) and math.isfinite(v)]
        low = min(values, key=lambda pair: pair[1]) if values else None
        high = max(values, key=lambda pair: pair[1]) if values else None
        spread = round(high[1] - low[1], 1) if len(values) >= 2 else None
        crosses = bool(key == 'gust' and low and high and
                       low[1] < limits['gust_relevant_kmh'] <= high[1])
        result[key] = {'spread': spread, 'threshold': threshold,
                       'relevant': spread is not None and (spread >= threshold or crosses),
                       'crosses_gust_threshold': crosses,
                       'low': {'id': low[0]['id'], 'name': low[0]['name'], 'value': low[1]} if low else None,
                       'high': {'id': high[0]['id'], 'name': high[0]['name'], 'value': high[1]} if high else None,
                       'available_locations': len(values)}
    result['has_contrast'] = any(item['relevant'] for item in result.values())
    return result

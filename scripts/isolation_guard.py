from pathlib import Path
BAD=['@previsaosulflu','previsaovr','27148485038175']
roots=[Path('src'),Path('.github')]
viol=[]
for root in roots:
    for p in root.rglob('*'):
        if p.is_file():
            try: t=p.read_text(encoding='utf-8').casefold()
            except Exception: continue
            for bad in BAD:
                if bad.casefold() in t: viol.append((str(p),bad))
if viol:
    raise SystemExit('isolamento falhou: '+repr(viol))
print('isolation_guard: ok')

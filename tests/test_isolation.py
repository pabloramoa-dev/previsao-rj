from pathlib import Path

def test_runtime_has_no_old_account_handle_or_id():
    bad=['@previsaosulflu','previsaovr','27148485038175']
    text='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for r in [Path('src'),Path('.github')] for p in r.rglob('*') if p.is_file())
    low=text.casefold()
    for item in bad: assert item.casefold() not in low

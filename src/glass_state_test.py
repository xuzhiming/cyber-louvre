import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import time, json
from playwright.sync_api import sync_playwright
errors=[]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + _REPO + '/web/preview.html')
    pg.wait_for_function('window.__ready === true', timeout=240000)
    for m in ('day','night','day'):
        pg.evaluate(f"window.__fx.setMode('{m}')"); print(m, pg.evaluate('window.__fx.state().glass'))
    print('errors', errors); b.close()

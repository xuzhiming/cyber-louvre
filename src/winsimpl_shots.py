import sys, time, json
from playwright.sync_api import sync_playwright
html, prefix = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/ws/'
errors = []
V = {'facade': ([0, 20, 78], [0, 9, 0], 55), 'wing': ([-112, 14, 48], [-74, 9, 2], 48), 'room': ([-66.7, 2.4, 23.0], [-74.6, 3.6, 25.5], 80)}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    for mode in ('day', 'night'):
        pg.evaluate(f"window.__fx.setMode('{mode}')"); time.sleep(2)
        for n, (c, t, f) in V.items():
            pg.evaluate(f"window.__cam({c},{t},{f})"); time.sleep(2.5)
            pg.screenshot(path=f'{SH}{prefix}_{n}_{mode}.png', timeout=180000)
    print(json.dumps({'errors': errors})); b.close()

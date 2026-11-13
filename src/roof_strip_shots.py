"""t38u: day views of the roof light strips.  usage: roof_strip_shots.py FILE_URL OUTPREFIX"""
import sys, time
from playwright.sync_api import sync_playwright
url, pre = sys.argv[1], sys.argv[2]
V = {'hero': ([135, 78, 150], [0, 22, 0]), 'pav': ([95, 52, 95], [62, 34, 47])}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1100, 'height': 650}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.goto(url + ('&' if '?' in url else '?') + 'mode=day&minimap=0'); pg.wait_for_function('window.__ready === true', timeout=240000); time.sleep(1.5)
    for k, (pp, tt) in V.items():
        pg.evaluate(f"window.__cam({pp},{tt},35)"); time.sleep(2.5); pg.screenshot(path=f'{pre}_{k}.png')
    pg.evaluate("window.__fx.setMode('night')"); pg.evaluate(f"window.__cam({V['pav'][0]},{V['pav'][1]},35)"); time.sleep(2.5); pg.screenshot(path=f'{pre}_night_pav.png')
    print('fx', pg.evaluate('window.__fx.state()')['mode'], 'errors', errs[:5])
    b.close()

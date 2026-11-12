"""Interior views of the corner towers (pavilions) per storey, web viewer.  usage: tower_shots.py URL TAG"""
import sys, time
from playwright.sync_api import sync_playwright
url, tag = sys.argv[1], sys.argv[2]
OUT = '/workspace/outputs/cyber_louvre/renders/tower/'
import os; os.makedirs(OUT, exist_ok=True)
Z = {'L1': 0.0, 'L2': 8.0, 'L3': 16.0}
# (name, eye xy, target xy): NW tower hall looking SE to the wing / north-wing neighbour rooms; NW lobby side; SW tower
VIEWS = [('NW_hall_to_rooms', (-67.5, 55.5), (-55.0, 31.0)), ('NW_hall_to_lobby', (-56.5, 50.5), (-77.0, 37.0)),
         ('SW_hall_to_rooms', (-67.5, -55.5), (-55.0, -31.0))]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1200, 'height': 720}); errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000)
    for lv in ('L1', 'L2', 'L3'):
        for name, e, t in VIEWS:
            if name.startswith('SW') and lv != 'L1': continue
            z = Z[lv]
            pg.evaluate(f"window.__cam([{e[0]},{z + 1.7},{-e[1]}],[{t[0]},{z + 1.5},{-t[1]}],78)")
            time.sleep(6)
            pg.screenshot(path=f'{OUT}{name}_{lv}_{tag}.png')
    print('errors', errs[:5])
    b.close()

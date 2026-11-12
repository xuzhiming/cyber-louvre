import sys, time, json
from playwright.sync_api import sync_playwright
html, prefix = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/or/'
errors = []
# three = (x, z, -y)
V = {'wcorr': ([-64.6, 1.8, 31.0], [-62.0, 1.9, -6.0], 72),        # W wing 1F corridor looking north, room side on the right
     'ncorr': ([-15.5, 9.8, -40.6], [-50.0, 9.6, -38.4], 72),      # NW wing 2F corridor looking west, S-row rooms on the left
     'bay':   ([-65.6, 1.8, 8.5], [-54.0, 2.6, 8.5], 84)}          # W_IN1 1F seen from the corridor
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate("window.__fx.setMode('day')"); time.sleep(2)
    for n, (c, t, f) in V.items():
        pg.evaluate(f"window.__cam({c},{t},{f})"); time.sleep(2.5)
        pg.screenshot(path=f'{SH}{prefix}_{n}.png', timeout=180000)
    print(json.dumps({'errors': errors})); b.close()

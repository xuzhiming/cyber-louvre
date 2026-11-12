import sys, time, json
from playwright.sync_api import sync_playwright
url, prefix = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/art/'
errors = []
V = {'in3': ([-58.2, 1.7, -27.0], [-58.2, 1.6, -34.0], 70), 'out0': ([-69.8, 1.7, 23.5], [-69.8, 1.6, 34.0], 70),
     'bay': ([-64.5, 1.8, -18.5], [-55.0, 1.6, -30.0], 75), 'nw': ([-47.3, 1.7, -35.5], [-54.0, 1.6, -35.5], 70)}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto(url)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    for mode in sys.argv[3].split(','):
        pg.evaluate(f"window.__fx.setMode('{mode}')"); time.sleep(1.5)
        for n, (c, t, f) in V.items():
            pg.evaluate(f"window.__cam({c},{t},{f})")
            for _ in range(30):
                time.sleep(1)
                st = pg.evaluate("window.__art ? window.__art.state() : null")
                if st is None or st['loading'] == 0 and _ > 6: break
            time.sleep(2)
            pg.screenshot(path=f'{SH}{prefix}_{n}_{mode}.png', timeout=180000)
    print(json.dumps({'errors': errors})); b.close()

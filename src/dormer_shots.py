import sys, time, json
from playwright.sync_api import sync_playwright
html, prefix = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/cg5/'
errors = []
EXT = "window.__cam([-58,32,76],[-67,28.2,61],40)"
ATT = "window.__cam([-67,26.4,57.0],[-67,28.4,62],75)"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    def shot(n): time.sleep(2.0); pg.screenshot(path=SH + prefix + '_' + n + '.png', timeout=180000)
    pg.evaluate("window.__fx.setMode('day')"); time.sleep(1)
    pg.evaluate(EXT); shot('dormer_day')
    pg.evaluate(ATT); shot('attic_day')
    pg.evaluate("window.__fx.setMode('night')")
    pg.evaluate(EXT); shot('dormer_night')
    pg.evaluate(ATT); shot('attic_night')
    print(json.dumps({'errors': errors})); b.close()

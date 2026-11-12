import sys, time, json
from playwright.sync_api import sync_playwright
html, prefix = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/cg4/'
errors = []; out = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    def shot(n): time.sleep(2.0); pg.screenshot(path=SH + prefix + '_' + n + '.png', timeout=180000)
    # hero: day then night
    pg.evaluate("window.__fx.setMode('day')"); pg.evaluate("window.__goTo('front')"); time.sleep(3)
    pg.evaluate("window.__cam([-95,38,125],[-60,14,40],38)"); shot('ext_day')
    pg.evaluate("window.__cam([-92,42,78],[-68,35,47],45)"); shot('roof_day')
    pg.evaluate("window.__fx.setMode('night')")
    pg.evaluate("window.__cam([-95,38,125],[-60,14,40],38)"); shot('ext_night')
    pg.evaluate("window.__cam([-92,42,78],[-68,35,47],45)"); shot('roof_night')
    out['errors'] = errors; print(json.dumps(out))
    b.close()

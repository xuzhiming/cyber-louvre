"""Reproduce / verify slot S032 (NW_N2_L1, GIF work 1844383116844732416): stand in front of it, log network + console."""
import json, math, time, sys
from playwright.sync_api import sync_playwright
url, tag = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/art/'
errors, reqs, resp = [], [], {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.on('request', lambda r: reqs.append(r.url))
    pg.on('response', lambda r: resp.__setitem__(r.url, (r.status, r.headers.get('content-type'), r.headers.get('content-length'))))
    pg.goto(url)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate("window.__fx.setMode('day')"); time.sleep(1)
    pg.evaluate("window.__cam([-23.0, 1.7, -43.9], [-27.1, 1.6, -43.9], 60)")
    for _ in range(40):
        time.sleep(1); st = pg.evaluate('window.__art.state()')
        if st['loading'] == 0 and _ > 8: break
    time.sleep(3); pg.screenshot(path=SH + f'gif_{tag}_a.png', timeout=180000)
    time.sleep(1.5); pg.screenshot(path=SH + f'gif_{tag}_b.png', timeout=180000)
    it = pg.evaluate("(() => { const s = window.__art.slot ? window.__art.slot('S032') : null; return s; })()")
    gif = [u for u in reqs if 'QmRGBuq' in u]
    print(json.dumps(dict(state=st, slot=it, gif_requests=[(u[:160], resp.get(u)) for u in gif], console=errors[:10]), indent=1, ensure_ascii=False))
    b.close()

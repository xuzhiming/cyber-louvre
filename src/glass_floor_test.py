import time, json, math, sys
from playwright.sync_api import sync_playwright
html = sys.argv[1] if len(sys.argv) > 1 else '/workspace/outputs/cyber_louvre/web/preview.html'
errors=[]; out={}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.keyboard.press('KeyF'); time.sleep(1)
    s = pg.evaluate('window.__walk.state()')
    if s['fly']: pg.keyboard.press('KeyG')
    # floor-to-ceiling room window on WING_W west face (x=-74, y -28..-23, sill 0.08) ; tall hall window on LOBBY / walk both ways
    # face = outer glass plane; a blocked walker stops ~RAD (0.35 m) short of it
    tests = {'room window W_OUT0 from outside (+x)': (-75.6, -25.5, 0.0, 'x', +1, -74.48),
             'room window W_OUT0 from inside (-x)': (-70.0, -25.5, 0.0, 'x', -1, -74.48),
             'room window NW_N1 from outside (-y)': (-34.0, 51.6, 0.0, 'y', -1, 50.45),
             'room window NW_N1 from inside (+y)': (-34.0, 48.6, 0.0, 'y', +1, 50.45)}
    for name, (x, y, z, ax, d, face) in tests.items():
        res = {('x', 1): -math.pi / 2, ('x', -1): math.pi / 2, ('y', 1): 0.0, ('y', -1): math.pi}[(ax, d)]   # three.js yaw: 0 looks +y(world)
        pg.evaluate(f'window.__walk.place({x},{y},{z},{res})'); time.sleep(0.6)
        pg.keyboard.down('KeyW'); time.sleep(4); pg.keyboard.up('KeyW')
        s = pg.evaluate('window.__walk.state()')
        crossed = (s[ax] - face) * d > 0
        out[name] = dict(end=round(s[ax], 2), face=face, blocked=not crossed)
    out['errors'] = errors; print(json.dumps(out, indent=1)); b.close()

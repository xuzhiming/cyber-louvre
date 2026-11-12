import time, json
from playwright.sync_api import sync_playwright
errors=[]; out={}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file:///workspace/outputs/cyber_louvre/web/preview.html')
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.keyboard.press('KeyF'); time.sleep(1); pg.keyboard.press('KeyG')   # fly mode
    for name, (x, y, z, yaw, wallface) in {'L2 window y=-60 (flying, facing +y)': (-63.3, -66, 11.0, 0, -60.4), 'L1 arch window (walking)': (-63.3, -64, 0.0, 0, -60.4)}.items():
        pg.evaluate(f'window.__walk.place({x},{y},{z},{yaw})'); time.sleep(0.8)
        if 'walking' in name: 
            s=pg.evaluate('window.__walk.state()');
            if s['fly']: pg.keyboard.press('KeyG')
        pg.keyboard.down('KeyW'); time.sleep(4); pg.keyboard.up('KeyW')
        s = pg.evaluate('window.__walk.state()')
        out[name] = dict(end_y=round(s['y'], 2), end_z=round(s['z'], 2), blocked=s['y'] < wallface)
    out['errors'] = errors; print(json.dumps(out, indent=1)); b.close()

"""Headless-Chrome walk test through the opened gallery bays: corridor -> room -> corridor (W wing 1F, NW wing 2F)."""
import json, math, time, sys
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'
SH = ROOT + 'renders/walk/'
html = sys.argv[1] if len(sys.argv) > 1 else ROOT + 'web/preview.html'
ROUTES = {
  # legs enter the bays OFF the old door axis (old doors were 2.4 m wide, centred) -> only passable with the door wall gone
  'W_wing_1F': [(-64, 0, 0), (-64, -14.5, 0), (-59, -14.5, 0), (-59.5, -4, 0), (-64, -3.5, 0), (-64, -21, 0), (-70.5, -21, 0),
                (-64, -30, 0), (-58, -30, 0), (-64, -22, 0), (-64, -5, 0)],
  'NW_wing_2F': [(-30, 40, 8), (-38.5, 40, 8), (-38.5, 34, 8), (-30, 33, 8), (-29.5, 40, 8), (-24, 40, 8), (-24, 46, 8), (-24, 40, 8), (-17, 40, 8),
                 (-17, 46.5, 8), (-17, 40, 8), (-50.5, 40, 8), (-50.5, 33.5, 8), (-50.5, 40, 8)],
  'E_wing_3F': [(64, 0, 16), (64, 3, 16), (58.5, 3, 16), (64, 14, 16), (64, 30, 16), (70.5, 30, 16), (64, 20, 16)],
}
res = {}; errors = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 640, 'height': 360})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + html)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    st = lambda: pg.evaluate('window.__walk.state()')
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    def steer(target, tol, timeout):
        t0 = time.time(); last = None; lastmove = time.time(); ok = False
        pg.keyboard.down('KeyW')
        while time.time() - t0 < timeout:
            s = st(); dx, dy = target[0] - s['x'], target[1] - s['y']
            if math.hypot(dx, dy) < tol: ok = True; break
            pg.evaluate(f'window.__walk.setLook({math.atan2(-dx, dy)}, 0)')
            if last is None or math.hypot(s['x'] - last[0], s['y'] - last[1]) > 0.15: last = (s['x'], s['y']); lastmove = time.time()
            elif time.time() - lastmove > 8: break
            time.sleep(0.05)
        pg.keyboard.up('KeyW')
        return ok, st()
    for name, pts in ROUTES.items():
        pg.evaluate('window.__walk.setPos(%f,%f,%f)' % pts[0]); time.sleep(1.0)
        stuck = None; zr = []; t0 = time.time()
        for i, q in enumerate(pts[1:], 1):
            ok, s = steer(q, 0.5, 70); zr.append(s['z'])
            if not ok: stuck = (i, q, (round(s['x'], 2), round(s['y'], 2), round(s['z'], 2))); break
            if i == 3: pg.screenshot(path=SH + 'openroom_%s%s.png' % (name, '' if len(sys.argv) < 3 else '_' + sys.argv[2]), timeout=180000)
        s = st()
        res[name] = dict(final=(round(s['x'], 2), round(s['y'], 2), round(s['z'], 3)), floor=s['floor'], z_range=(round(min(zr), 3), round(max(zr), 3)),
                         stuck=stuck, waypoints=len(pts) - 1, secs=round(time.time() - t0))
        print(name, res[name], flush=True)
    print('console errors:', errors)
    json.dump({'res': res, 'errors': errors}, open(SH + 'walk_openrooms%s.json' % ('' if len(sys.argv) < 3 else '_' + sys.argv[2]), 'w'))
    b.close()

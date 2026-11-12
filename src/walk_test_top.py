"""Headless-Chrome walk test: climb each corner tower (shaft L1 -> L4 mech level) and the central building (plaza -> main door ->
lobby -> grand stairs -> L3 -> ring balcony north side).  Only W / mouse-look, no jump."""
import json, math, time, sys, os
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'
SH = ROOT + 'renders/walk/'
towers = json.load(open(ROOT + 'src/test_route_towers.json'))
central = json.load(open(ROOT + 'src/test_route_central_top.json'))['RN_L3']['pts']
res = {}; errors = []
def L(*a): print(' '.join(str(x) for x in a), flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 640, 'height': 360})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + ROOT + 'web/preview.html')
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    st = lambda: pg.evaluate('window.__walk.state()')
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    def steer(target, tol, run, timeout, traj):
        t0 = time.time(); last = None; lastmove = time.time()
        pg.keyboard.down('KeyW')
        if run: pg.keyboard.down('ShiftLeft')
        ok = False
        while time.time() - t0 < timeout:
            s = st(); traj.append((s['x'], s['y'], s['z']))
            dx, dy = target[0] - s['x'], target[1] - s['y']
            if math.hypot(dx, dy) < tol: ok = True; break
            pg.evaluate(f'window.__walk.setLook({math.atan2(-dx, dy)}, 0)')
            if last is None or math.hypot(s['x'] - last[0], s['y'] - last[1]) > 0.15: last = (s['x'], s['y']); lastmove = time.time()
            elif time.time() - lastmove > 8: break
            time.sleep(0.05)
        pg.keyboard.up('KeyW')
        if run: pg.keyboard.up('ShiftLeft')
        return ok, st()
    def walk(pts, name):
        traj = []; stuck = None; zmax = -9; t0 = time.time()
        for i, q in enumerate(pts[1:], 1):
            near = any(abs(pts[j][2] - pts[j - 1][2]) > 0.01 for j in range(max(1, i - 1), min(len(pts), i + 2)))
            run = (not near) and math.hypot(q[0] - st()['x'], q[1] - st()['y']) > 6
            ok, s = steer((q[0], q[1]), 0.45 if near else 0.8, run, 40, traj)
            if not ok: stuck = (i, q, (round(s['x'], 2), round(s['y'], 2), round(s['z'], 2))); break
            zmax = max(zmax, s['z'])
        s = st()
        res[name] = dict(final=(round(s['x'], 2), round(s['y'], 2), round(s['z'], 3)), floor=s['floor'], zmax=round(zmax, 3), stuck=stuck, secs=round(time.time() - t0), traj=traj)
        L(name, 'final', res[name]['final'], s['floor'], 'zmax', res[name]['zmax'], 'stuck', stuck, 'secs', res[name]['secs'])
        pg.screenshot(path=SH + 'top_%s.png' % name, timeout=180000)
    for q in ('NW', 'NE', 'SW', 'SE'):
        pts = towers[q]['pts']
        pg.evaluate('window.__walk.setPos(%f,%f,%f)' % tuple(pts[0])); time.sleep(0.8)
        walk(pts, 'tower_' + q)
    pg.evaluate('window.__walk.teleport("plaza")'); time.sleep(0.6)
    walk(central, 'central')
    L('console errors:', errors)
    json.dump({'res': res, 'errors': errors}, open(SH + 'walk_top.json', 'w'))
    b.close()

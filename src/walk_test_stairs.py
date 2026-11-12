"""Headless-Chrome walk test: plaza -> main door -> lobby -> grand stair (L1->L2) -> gallery -> grand stair (L2->L3) -> L3.
Only W (+Shift on long straight legs) and mouse-look; no jump."""
import json, math, time, sys, os
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'
SH = ROOT + 'renders/walk/'
route = json.load(open(ROOT + 'src/test_route_stairs.json'))['GL3']['pts']
log = []; errors = []
def L(*a):
    s = ' '.join(str(x) for x in a); print(s); log.append(s)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 800, 'height': 450})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + ROOT + 'web/preview.html')
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=180000)
    st = lambda: pg.evaluate('window.__walk.state()')
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    assert st()['on']
    pg.evaluate('window.__walk.teleport("plaza")'); time.sleep(0.6)
    traj = []
    def steer(target, tol, run, timeout):
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
            elif time.time() - lastmove > 6: break
            time.sleep(0.05)
        pg.keyboard.up('KeyW')
        if run: pg.keyboard.up('ShiftLeft')
        return ok, st()
    pts = route; shots = {}; stuck = None; zmax = -9; seq = []
    def shot(name, look=None):
        if look: pg.evaluate(f'window.__walk.setLook({look[0]}, {look[1]})'); time.sleep(0.4)
        pg.screenshot(path=SH + name, timeout=180000)
    t_start = time.time()
    for i, q in enumerate(pts[1:], 1):
        near_stair = any(abs(pts[j][2] - pts[j - 1][2]) > 0.01 for j in range(max(1, i - 1), min(len(pts), i + 2)))
        run = not near_stair and math.hypot(q[0] - st()['x'], q[1] - st()['y']) > 6
        ok, s = steer((q[0], q[1]), 0.45 if near_stair else 0.8, run, 40)
        if not ok: stuck = (i, q, (round(s['x'], 2), round(s['y'], 2), round(s['z'], 2))); break
        zmax = max(zmax, s['z']); seq.append((round(s['x'], 2), round(s['y'], 2), round(s['z'], 2)))
        if 'door' not in shots and abs(s['y'] - 8.0) < 0.8 and s['z'] < 0.1 and s['x'] ** 2 < 4:
            shot('s01_main_door.png'); shots['door'] = 1
        if 'lobby' not in shots and s['y'] > 11 and s['z'] < 0.1:
            shot('s02_lobby_inside.png'); shots['lobby'] = 1
        for key, zlo, zhi, nm in (('c1', 2.5, 2.85, 's03_grand_landing1.png'), ('c2', 5.2, 5.5, 's04_grand_landing2.png'),
                                  ('gl2', 7.95, 8.1, 's05_gallery_L2.png'), ('t12', 11.9, 12.1, 's06_gr2_turn_landing.png'),
                                  ('gl3', 15.95, 16.1, 's07_arrived_L3.png')):
            if key not in shots and zlo < s['z'] < zhi and s['y'] > 8:
                shot(nm); shots[key] = 1
        if 'foot' not in shots and s['y'] > 10.5 and abs(abs(s['x']) - 10.7) < 1.5 and s['z'] < 0.1:
            shot('s02b_foot_of_grand_stair.png'); shots['foot'] = 1
    s = st()
    L('FINAL pos', round(s['x'], 2), round(s['y'], 2), 'height', round(s['z'], 3), s['floor'], 'time', round(time.time() - t_start), 's', 'stuck:', stuck)
    L('zmax', round(zmax, 2), 'milestone shots', sorted(shots))
    pg.evaluate('window.__walk.setLook(math.pi, -0.15)'.replace('math.pi', '3.14159')); time.sleep(0.6)
    pg.screenshot(path=SH + 's08_L3_look_back.png', timeout=180000)
    L('console errors:', errors)
    json.dump({'traj': traj, 'stuck': stuck, 'log': log, 'errors': errors, 'zmax': zmax, 'seq': seq}, open(SH + 'walk_stairs.json', 'w'))
    b.close()

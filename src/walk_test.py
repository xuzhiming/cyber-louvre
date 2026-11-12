import json, math, time, sys, os
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'
SH = ROOT + 'renders/walk/'
route = json.load(open(ROOT + 'src/test_route.json'))['GL2']['pts']
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
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=120000)
    st = lambda: pg.evaluate('window.__walk.state()')
    L('loaded; collision bvh', st()['bvh'], 'tris', st()['tris'])
    pg.screenshot(path=SH + '00_orbit.png')
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    s = st(); L('after F:', s)
    assert s['on']
    pg.screenshot(path=SH + '01_plaza_spawn.png')
    traj = []
    def steer(target, tol, run, timeout, label):
        t0 = time.time(); last = None; lastmove = time.time()
        pg.keyboard.down('KeyW')
        if run: pg.keyboard.down('ShiftLeft')
        ok = False
        while time.time() - t0 < timeout:
            s = st(); traj.append((s['x'], s['y'], s['z']))
            dx, dy = target[0] - s['x'], target[1] - s['y']
            d = math.hypot(dx, dy)
            if d < tol: ok = True; break
            # blender dir (dx,dy) -> three look yaw: dir=(-sin,-cos) in (x,z=-y) => (dx,dy)=(-sin yaw, cos yaw)
            yaw = math.atan2(-dx, dy)
            pg.evaluate(f'window.__walk.setLook({yaw}, 0)')
            if last is None or math.hypot(s['x'] - last[0], s['y'] - last[1]) > 0.15: last = (s['x'], s['y']); lastmove = time.time()
            elif time.time() - lastmove > 6: break
            time.sleep(0.05)
        pg.keyboard.up('KeyW')
        if run: pg.keyboard.up('ShiftLeft')
        return ok, st()
    # --- negative test: walk straight into the pyramid glass wall (x=10, y=-69 -> north)
    pg.evaluate('window.__walk.setPos(10,-69,0)')
    time.sleep(0.5)
    ok, s = steer((10, -40), 0.5, False, 12, 'wall')
    L('NEG pyramid wall: reached y=-40?', ok, 'stopped at', round(s['x'], 2), round(s['y'], 2), 'z', round(s['z'], 2))
    wall_ok = s['y'] < -65.5
    pg.screenshot(path=SH + '02_blocked_by_pyramid_wall.png')
    # --- positive: plaza -> pyramid door -> foyer -> B1 -> lobby -> grand stairs -> 2F
    pg.evaluate('window.__walk.teleport("plaza")'); time.sleep(0.6)
    traj.clear()
    pts = route
    shots = {}
    # decimate: keep every point for stairs (small spacing) but use looser tol on long straight legs
    t_start = time.time(); stuck = None; zmax = -9; zmin = 9
    for i, q in enumerate(pts[1:], 1):
        zq = q[2]
        near_stair = any(abs(pts[j][2] - pts[j - 1][2]) > 0.01 for j in range(max(1, i - 1), min(len(pts), i + 2)))
        run = not near_stair and math.hypot(q[0] - st()['x'], q[1] - st()['y']) > 6
        tol = 0.45 if near_stair else 0.8
        ok, s = steer((q[0], q[1]), tol, run, 40, i)
        if not ok:
            stuck = (i, q, (round(s['x'], 2), round(s['y'], 2), round(s['z'], 2))); break
        if i % 20 == 0: L('wp', i, 'of', len(pts) - 1, 'pos', round(s['x'], 1), round(s['y'], 1), 'h', round(s['z'], 2), s['floor'])
        zmax = max(zmax, s['z']); zmin = min(zmin, s['z'])
        # screenshots at milestones
        if 'door' not in shots and q[1] > -64 and zq == 0 and s['y'] > -64.5:
            pg.screenshot(path=SH + '03_pyramid_door.png'); shots['door'] = 1
        if 'b1' not in shots and s['z'] < -5.5:
            pg.screenshot(path=SH + '04_b1_hall.png'); shots['b1'] = 1
        if 'lobby' not in shots and zmin < -5 and s['z'] > -0.2 and s['y'] > 8:
            pg.screenshot(path=SH + '05_lobby.png'); shots['lobby'] = 1
        if 'stairs' not in shots and 3.5 < s['z'] < 4.6 and s['y'] > 8:
            pg.screenshot(path=SH + '06_on_grand_stairs.png'); shots['stairs'] = 1
    s = st()
    L('FINAL pos', round(s['x'], 2), round(s['y'], 2), 'height', round(s['z'], 3), s['floor'], 'time', round(time.time() - t_start), 's', 'stuck:', stuck)
    pg.screenshot(path=SH + '07_arrived_2F.png')
    # look back down toward the atrium
    pg.evaluate('window.__walk.setLook(0, -0.2)'); time.sleep(0.8)
    pg.screenshot(path=SH + '08_2F_atrium_view.png')
    # fly mode + teleports + hud
    pg.keyboard.press('KeyG'); pg.keyboard.down('Space'); time.sleep(1.5); pg.keyboard.up('Space')
    L('fly up:', round(st()['z'], 2), 'fly', st()['fly']); pg.keyboard.press('KeyG')
    for name, key in [('lobby', 'Digit2'), ('f3', 'Digit5'), ('pav', 'Digit6'), ('b1', 'Digit7')]:
        pg.keyboard.press(key); time.sleep(1.5); s = st(); L('teleport', name, round(s['x'], 1), round(s['y'], 1), round(s['z'], 2), s['floor'], 'grounded', s['grounded'])
        pg.screenshot(path=SH + f'09_tp_{name}.png')
    # jump
    pg.keyboard.press('Digit2'); time.sleep(1.2); z0 = st()['z']; pg.keyboard.press('Space'); zm = z0
    t0 = time.time()
    while time.time() - t0 < 1.2: zm = max(zm, st()['z'])
    L('jump apex +', round(zm - z0, 2), 'm; grounded after', st()['grounded'])
    # mouse drag fallback look
    pg.mouse.move(400, 225); pg.mouse.down(); pg.mouse.move(520, 225, steps=5); pg.mouse.up(); time.sleep(0.3)
    L('yaw after drag', round(st()['yaw'], 3))
    # exit walk mode and check orbit buttons
    pg.keyboard.press('KeyF'); time.sleep(1); L('back to orbit', st()['on'])
    pg.click('[data-view=hero]'); time.sleep(1.5)
    pg.click('[data-cut=cut]'); time.sleep(1.0)
    pg.screenshot(path=SH + '10_orbit_cutaway_after_walk.png')
    L('console errors:', errors)
    # pass-through check of the walked trajectory with the real mesh BVH
    json.dump({'traj': traj, 'stuck': stuck, 'wall_ok': wall_ok, 'log': log, 'errors': errors, 'zmin': zmin, 'zmax': zmax}, open(SH + 'walk_test.json', 'w'))
    b.close()

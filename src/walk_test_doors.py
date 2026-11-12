"""Walk into each of the 3 pyramids and through the lobby auto door WITHOUT jumping; check the doors animate (closed -> open)."""
import json, math, time
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'; SH = ROOT + 'renders/walk/'
log = []; errors = []; keys_used = set()
def L(*a):
    s = ' '.join(str(x) for x in a); print(s); log.append(s)
CASES = [  # name, door id, start (x,y), via waypoint (x,y), door line, goal inside (x,y)
    ('main_pyramid', 'PYR_MAIN', (7, -69.3), (0, -69.0), (0, -66), (0, -61.0)),
    ('small_pyramid_L', 'PYR_SL', (-44, -60), (-37, -60.0), (-37, -58), (-37, -54.5)),
    ('small_pyramid_R', 'PYR_SR', (44, -60), (37, -60.0), (37, -58), (37, -54.5)),
    ('lobby_main_door', 'LOBBY', (0, -2), (0, 3), (0, 8), (0, 14)),
]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + ROOT + 'web/preview.html')
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=120000)
    st = lambda: pg.evaluate('window.__walk.state()')
    doors = lambda: {d['id']: d['open'] for d in pg.evaluate('window.__doors()')}
    L('doors in model:', pg.evaluate('window.__doors()'))
    pg.keyboard.press('KeyF'); time.sleep(1.0)
    results = []
    for name, did, start, via, line, goal in CASES:
        pg.evaluate(f'window.__walk.setPos({start[0]},{start[1]},0)')
        yaw = math.atan2(-(via[0] - start[0]), via[1] - start[1])
        pg.evaluate(f'window.__walk.setLook({yaw},0)'); time.sleep(1.2)
        closed = doors()[did]
        pg.screenshot(path=SH + f'door_{name}_1_closed.png')
        pg.keyboard.down('KeyW'); keys_used.add('KeyW')
        passed_via = False; t0 = time.time(); opened_seen = 0.0; reached = False; maxstep = 0.0; zprev = st()['z']; zs = []; shot_open = False
        while time.time() - t0 < 60:
            s = st(); zs.append(s['z']); maxstep = max(maxstep, abs(s['z'] - zprev)); zprev = s['z']
            o = doors()[did]; opened_seen = max(opened_seen, o)
            if not shot_open and o > 0.95 and math.hypot(s['x'] - line[0], s['y'] - line[1]) < 3.2:
                pg.screenshot(path=SH + f'door_{name}_2_open.png'); shot_open = True
            if math.hypot(s['x'] - goal[0], s['y'] - goal[1]) < 0.5: reached = True; break
            tgt = via if (not passed_via and math.hypot(s['x'] - via[0], s['y'] - via[1]) > 0.5) else goal
            if tgt is goal: passed_via = True
            pg.evaluate(f'window.__walk.setLook({math.atan2(-(tgt[0]-s["x"]), tgt[1]-s["y"])},0)')
            time.sleep(0.04)
        pg.keyboard.up('KeyW')
        s = st(); time.sleep(0.3)
        pg.screenshot(path=SH + f'door_{name}_3_inside.png')
        r = dict(case=name, door=did, door_closed_at_start=closed, max_open_seen=opened_seen, reached_inside=reached, final=(round(s['x'], 2), round(s['y'], 2), round(s['z'], 3)),
                 max_height_change_between_samples_m=round(maxstep, 3), min_height=round(min(zs), 3), max_height=round(max(zs), 3), grounded=s['grounded'], screenshot_open=shot_open)
        results.append(r); L(r)
    # walk away -> doors close again
    pg.evaluate('window.__walk.setPos(0,-30,0)'); time.sleep(2.5)
    L('doors after walking away:', doors())
    # leave walk mode -> orbit still works
    pg.keyboard.press('KeyF'); time.sleep(0.8); pg.click('[data-view=front]'); time.sleep(1.5)
    pg.screenshot(path=SH + 'doors_orbit_front.png')
    L('console errors:', errors); L('keys pressed during door tests:', sorted(keys_used), '(no Space => no jumping)')
    json.dump(dict(results=results, errors=errors, keys=sorted(keys_used), log=log), open(SH + 'walk_test_doors.json', 'w'), indent=1)
    b.close()

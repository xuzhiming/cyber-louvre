"""t37u click-to-focus test.  For several works (text, plaintext, image, GIF, video, audio, bidder.top image + video): stand
~6 m away at an angle in walk mode, left-click the work where it is on screen -> camera flies (<=1.2 s) to stand in front of it
(same floor, eye 1.7 m, facing the frame, centred), info panel shows that work; then walking resumes, walk-away / Esc / x close
the panel; a drag never picks; movement cancels the flight; clicked video/audio becomes the active media; orbit-view click
enters walk mode; touch tap works.  usage: click_focus_test.py URL"""
import sys, time, json, math
from playwright.sync_api import sync_playwright
url = sys.argv[1]; R = '/workspace/outputs/cyber_louvre/renders/'
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
A = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json')); PL = A['placement']; W = A['artworks']
WORK = {sid: W[PL[k]] for k, sid in enumerate(S) if isinstance(PL[k], int)}
FL = {'L1': 0, 'L2': 8, 'L3': 16}
CASES = [('S000', 'text'), ('S012', 'plaintext'), ('S013', 'image'), ('S047', 'gif'), ('S027', 'video'), ('S129', 'audio'), ('S137', 'top image'), ('S139', 'top video'), ('S146', 'top image 3F')]
res, cons = [], []
def approach(pg, sid, back=6.0, side=1.6):
    s = S[sid]; x, y = s['pos'][:2]; nx, ny = s['normal'][:2]; tx, ty = -ny, nx
    px, py = x + nx * back + tx * side, y + ny * back + ty * side
    yaw = math.atan2(-(x - px), y - py)
    pg.evaluate(f"window.__walk.place({px}, {py}, {FL[s['band']]}, {yaw})")
    pg.wait_for_function('window.__walk.state().grounded', timeout=60000)      # (swiftshader can stall a few frames while textures upload)
    return px, py
def on_canvas(pg, x, y): return pg.evaluate(f"document.elementFromPoint({x},{y}).tagName") == 'CANVAS'
def hold_until(pg, key, metres, secs=20):      # swiftshader renders slowly (walk dt is clamped per frame) -> walk a distance, not a time
    s0 = pg.evaluate('window.__walk.state()'); pg.keyboard.down(key); t0 = time.time()
    while time.time() - t0 < secs:
        time.sleep(0.2); s = pg.evaluate('window.__walk.state()')
        if math.hypot(s['x'] - s0['x'], s['y'] - s0['y']) >= metres: break
    pg.keyboard.up(key); time.sleep(0.4); s = pg.evaluate('window.__walk.state()'); return round(math.hypot(s['x'] - s0['x'], s['y'] - s0['y']), 2)
def focus_click(pg, sid):
    pr = pg.evaluate(f"window.__focus.project('{sid}')"); assert on_canvas(pg, pr['x'], pr['y']), sid
    pg.mouse.click(pr['x'], pr['y']); pg.wait_for_function('!window.__focus.state().anim', timeout=15000); time.sleep(0.3)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 720})
    pg.on('console', lambda m: cons.append(m.text[:200]) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: cons.append('PAGEERROR ' + str(e)[:200]))
    pg.goto(url); pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate('window.__walk.enter()'); time.sleep(0.5)
    for n, (sid, label) in enumerate(CASES):
        w = WORK[sid]
        approach(pg, sid); time.sleep(1.2)
        # if the walker got pushed (partition), re-aim
        pr = pg.evaluate(f"window.__focus.project('{sid}')")
        ok_pick = pg.evaluate(f"window.__focus.pick({pr['x']}, {pr['y']})")
        if n == 2: pg.screenshot(path='/tmp/cf_before.png')
        n0 = pg.evaluate('window.__focus.state().n'); t0 = time.time()
        pg.mouse.click(pr['x'], pr['y'])
        st1 = pg.evaluate('window.__focus.state()')
        pg.wait_for_function('!window.__focus.state().anim', timeout=30000); dt = time.time() - t0
        time.sleep(0.3)
        pose = pg.evaluate(f"window.__focus.pose('{sid}')"); info = pg.evaluate('window.__art.info()')
        r = dict(slot=sid, case=label, picked=ok_pick, started=st1['n'] == n0 + 1 and st1['anim'], fly_s=round(dt, 2), pose=pose, info_slot=info and info['slot'],
                 title_ok=bool(info and info['title'] == (w['title'] or '').strip() or info and info['title'] == w['title']), href_ok=bool(info and info['href'] == w['detail_url']),
                 intro_shown=bool(info and (not w.get('intro') or w['intro'][:20] in info['text'])), source_label=bool(info and ('来源:' + (w.get('source') or 'bidder.art')) in info['text']))
        if label in ('video', 'audio', 'top video'):
            m = None
            for i in range(30):
                time.sleep(0.25); m = pg.evaluate('window.__art.media()')
                if m['cur'] == sid: break
            r['active_media'] = m['cur'] == sid; r['active_after_s'] = round(0.25 * (i + 1), 2); e = None
            for i in range(30):
                time.sleep(0.5); m = pg.evaluate('window.__art.media()'); e = next((e for e in m['els'] if e['slot'] == sid), None)
                if e and not e['paused'] and e['t'] > 0.2: break
            r['playing'] = bool(e and not e['paused'] and e['t'] > 0.2); r['unmuted'] = bool(e and not e['muted']); r['unpaused'] = m['unpaused']
        time.sleep(1.0); i2 = pg.evaluate('window.__art.info()'); r['thumb'] = bool(i2 and i2['thumb'])
        if not i2: r['closed'] = pg.evaluate('window.__focus.state()')
        r['anim_ms'] = next((l['dur'] for l in reversed(pg.evaluate('window.__focus.state().log')) if l.get('slot') == sid and 'dur' in l), None)
        if n == 2: pg.screenshot(path='/tmp/cf_after.png')
        if n in (4, 6): pg.screenshot(path=R + f'art/click_focus_{sid}.png')
        r['ok'] = bool(r['picked'] == sid and r['started'] and r['anim_ms'] <= 1200 and r['info_slot'] == sid and r['title_ok'] and r['href_ok'] and r['intro_shown'] and r['source_label']
                       and pose['along'] > 0.9 and pose['lateral'] < 0.35 and pose['facingDot'] > 0.97 and pose['centerDot'] > 0.995 and abs(pose['eyeAboveFloor'] - 1.7) < 0.02
                       and abs(pose['floorDelta']) < 0.1 and pose['walk'] and pose['grounded'] and r['thumb'] and r.get('active_media', True) and r.get('playing', True))
        res.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
    out = {}
    # walking resumes from the landing pose; walk-away closes the panel
    out['walk_resumes'] = hold_until(pg, 'KeyW', 0.4) >= 0.4 and pg.evaluate('window.__focus.state()')['open'] == 'S146'    # small step: panel stays
    out['walked_back_m'] = hold_until(pg, 'KeyS', 3.6)
    fs = pg.evaluate('window.__focus.state()'); out['walk_away'] = dict(open=fs['open'], closed=fs['closed'], why=fs['closeWhy'])
    out['walk_away_closes'] = fs['open'] is None and fs['closed'] == 'walk'
    # turn to another wall and walk a bit -> closes too (work out of view)
    approach(pg, 'S013', side=0); time.sleep(0.6); focus_click(pg, 'S013')
    pg.evaluate('window.__walk.setLook(window.__walk.state().yaw + Math.PI, 0)'); out['turned_walk_m'] = hold_until(pg, 'KeyW', 1.6)
    fs = pg.evaluate('window.__focus.state()'); out['turn_away'] = dict(open=fs['open'], closed=fs['closed'], why=fs['closeWhy'])
    out['turn_away_closes'] = fs['open'] is None and fs['closed'] == 'walk'
    # Esc closes
    approach(pg, 'S013', side=0); time.sleep(0.6); focus_click(pg, 'S013')
    pg.keyboard.press('Escape'); time.sleep(0.2); out['esc_closes'] = pg.evaluate('window.__focus.state()')['closed'] == 'esc' and not pg.is_visible('#artinfo')
    # x button closes
    approach(pg, 'S013', side=0); time.sleep(0.5); focus_click(pg, 'S013')
    pg.click('#artinfo .cls'); time.sleep(0.2); out['x_closes'] = pg.evaluate('window.__focus.state()')['closed'] == 'button' and not pg.is_visible('#artinfo')
    # a look-drag over a work never focuses it
    approach(pg, 'S014'); time.sleep(0.6); pr = pg.evaluate("window.__focus.project('S014')"); n0 = pg.evaluate('window.__focus.state().n')
    pg.mouse.move(pr['x'], pr['y']); pg.mouse.down(); pg.mouse.move(pr['x'] + 80, pr['y'], steps=6); pg.mouse.up(); time.sleep(0.3)
    out['drag_no_focus'] = pg.evaluate('window.__focus.state().n') == n0
    # movement cancels the flight (inside: walker stays where the camera was)
    approach(pg, 'S015', back=7, side=0); time.sleep(0.6); pr = pg.evaluate("window.__focus.project('S015')"); out['cancel_on_canvas'] = on_canvas(pg, pr['x'], pr['y']); out['locked'] = pg.evaluate('!!document.pointerLockElement')
    if out['locked']: pg.mouse.down(); pg.mouse.up()          # mouse is locked after the drag -> crosshair click (any mouse move would turn the view)
    else: pg.mouse.click(pr['x'], pr['y'])
    pg.keyboard.down('KeyW'); time.sleep(0.15); pg.keyboard.up('KeyW'); time.sleep(0.3)
    fs = pg.evaluate('window.__focus.state()'); pose = pg.evaluate("window.__focus.pose('S015')")
    out['move'] = dict(log=fs['log'][-3:], pose=pose, lastClick=fs['lastClick'])
    out['move_cancels'] = (not fs['anim']) and any(l.get('cancel') == 'key' for l in fs['log']) and pose['along'] > 2.3
    # orbit view click -> enters walk mode at the work
    s = S['S013']; x, y, z = s['pos']; nx, ny = s['normal'][:2]
    pg.evaluate('window.__walk.exit()'); pg.evaluate(f"window.__cam({[x + nx * 7, z + 0.5, -(y + ny * 7)]},{[x, z, -y]},35)"); time.sleep(0.8)
    focus_click(pg, 'S013')
    pose = pg.evaluate("window.__focus.pose('S013')"); out['orbit_click'] = dict(pose=pose, info=pg.evaluate('window.__art.info()')['slot'])
    out['orbit_click_ok'] = pose['walk'] and pose['lateral'] < 0.35 and pose['facingDot'] > 0.97 and out['orbit_click']['info'] == 'S013' and abs(pose['fov'] - 75) < 0.1
    out['minimap'] = pg.evaluate('window.__mm.draw()')
    out['console_errors'] = cons[:10]; out['art_errors'] = pg.evaluate('window.__art.state().errors')
    # touch tap (mobile viewport)
    pg.close()
    ctx = b.new_context(viewport={'width': 390, 'height': 760}, has_touch=True, is_mobile=True, device_scale_factor=1)
    tp = ctx.new_page(); tcons = []
    tp.on('pageerror', lambda e: tcons.append('PAGEERROR ' + str(e)[:200])); tp.on('console', lambda m: tcons.append(m.text[:200]) if m.type == 'error' else None)
    tp.goto(url, timeout=240000); tp.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    tp.evaluate('window.__walk.enter()'); approach(tp, 'S137', back=7, side=0.8); time.sleep(1.2)
    pr = tp.evaluate("window.__focus.project('S137')"); tp.touchscreen.tap(pr['x'], pr['y']); time.sleep(0.5); tp.wait_for_function('!window.__focus.state().anim', timeout=15000); time.sleep(0.5)
    pose = tp.evaluate("window.__focus.pose('S137')"); ti = tp.evaluate('window.__art.info()')
    out['touch'] = dict(pose=pose, info=ti and ti['slot'], console=tcons[:5]); out['touch_ok'] = bool(ti and ti['slot'] == 'S137' and pose['lateral'] < 0.35 and pose['facingDot'] > 0.97)
    tp.screenshot(path=R + 'art/click_focus_touch.png')
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
print('SUMMARY', json.dumps(dict(works_ok=sum(r['ok'] for r in res), works=len(res), failed=[r['slot'] for r in res if not r['ok']],
      **{k: out[k] for k in ('walk_resumes', 'walk_away_closes', 'turn_away_closes', 'esc_closes', 'x_closes', 'drag_no_focus', 'move_cancels', 'orbit_click_ok', 'touch_ok')}, console=len(cons))))

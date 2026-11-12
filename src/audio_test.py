"""Proximity audio + minimap test (t33u).  usage: audio_test.py URL [TAG]
Default Chrome autoplay policy (no flag): checks the locked->click unlock path, playback near (<6 m), hysteresis (7 m keeps
playing, quieter), stop far (>8 m) / other floor, resume; minimap floor switching, M toggle, zoom; screenshots."""
import sys, time, json
from playwright.sync_api import sync_playwright
url = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else 'local'
R = '/workspace/outputs/cyber_louvre/renders/art/'
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
SID = 'S129'; s = S[SID]; x, y, z = s['pos']; nx, ny = s['normal'][:2]; fz = 8.0
import math
yaw = math.atan2(nx, -ny)          # look against the slot normal: forward (-sin, cos) = (-nx, -ny)
res, cons, net = {}, [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=(['--autoplay-policy=document-user-activation-required'] if 'gesture' in tag else []) + ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 760})
    pg.on('console', lambda m: cons.append((m.type, m.text[:200])) if m.type in ('error',) else None)
    pg.on('pageerror', lambda e: cons.append(('pageerror', str(e)[:200])))
    pg.on('response', lambda r: net.append((r.status, r.url[:110])) if ('.mp3' in r.url or 'mp3' in r.url.lower()) else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000)
    pg.wait_for_function('window.__collisionReady === true', timeout=240000)
    A = lambda: pg.evaluate(f"window.__art.audio ? window.__art.audio('{SID}') : 'no-audio-hook'")
    AS = lambda: pg.evaluate("window.__art.audioState ? window.__art.audioState() : null")
    def at(d, zz=fz, wait=0.0):
        pg.evaluate(f"window.__walk.place({x + nx * d}, {y + ny * d}, {zz}, {yaw})")
        if wait: time.sleep(wait)
    res['fps'] = pg.evaluate("new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else r(+(n / 3).toFixed(1)); }; requestAnimationFrame(f); })")
    pg.evaluate("window.__walk.enter()")
    at(3, wait=5)
    res['near_before_gesture'] = A(); res['state_before_gesture'] = AS()
    pg.screenshot(path=R + f'audio_{tag}_locked.png')
    pg.mouse.click(640, 380)               # user gesture (also requests pointer lock)
    time.sleep(1.0); at(3, wait=2)
    a1 = A(); time.sleep(3); a2 = A()
    res['near_after_click'] = [a1, a2]; res['advancing_near'] = isinstance(a1, dict) and isinstance(a2, dict) and a2.get('t', 0) > a1.get('t', 0) and not a2.get('paused', True)
    res['state_after_click'] = AS()
    pg.screenshot(path=R + f'audio_{tag}_near.png')
    at(7, wait=2.5); h1 = A(); time.sleep(1.5); h2 = A()
    res['hyst_7m'] = [h1, h2]; res['playing_7m'] = isinstance(h2, dict) and not h2.get('paused', True) and h2.get('t', 0) > h1.get('t', 0)
    at(12, wait=1.5); f = A(); res['far_12m'] = f; res['paused_far'] = isinstance(f, dict) and f.get('paused') is True
    t_far = f.get('t') if isinstance(f, dict) else None; time.sleep(1.5); f2 = A(); res['far_still'] = isinstance(f2, dict) and f2.get('t') == t_far
    at(3, wait=3); r1 = A(); time.sleep(1.5); r2 = A()
    res['resume'] = [r1, r2]; res['resumed'] = isinstance(r2, dict) and not r2.get('paused', True) and r2.get('t', 0) > r1.get('t', 0)
    at(3, zz=0.0, wait=2.0); o = A(); res['other_floor_1F'] = o; res['paused_other_floor'] = (o is None) or (isinstance(o, dict) and (o.get('paused') is True or o.get('none')))
    # minimap
    mm = {}
    for tp in ['b1', 'plaza', 'lobby', 'f2', 'f3', 'pav']:
        pg.evaluate(f"window.__walk.teleport('{tp}')"); time.sleep(1.5); pg.evaluate("window.__mm.draw()"); mm[tp] = pg.evaluate("window.__mm.state()")
    pg.evaluate("window.__walk.place(40, 0, 24.05, 0)"); time.sleep(1.0); pg.evaluate("window.__mm.draw()"); mm['L4_mech'] = pg.evaluate("window.__mm.state().name")
    pg.evaluate("window.__walk.teleport('f2')"); time.sleep(0.6)
    pg.keyboard.press('KeyM'); time.sleep(0.4); mm['after_M'] = pg.evaluate("window.__mm.state().display")
    pg.keyboard.press('KeyM'); time.sleep(0.4); mm['after_M2'] = pg.evaluate("window.__mm.state().display")
    res['minimap'] = mm
    # screenshots: near the audio work with minimap (night), zoomed minimap, day mode
    at(2.6, wait=3.0)
    pg.evaluate("document.exitPointerLock && document.exitPointerLock()"); time.sleep(0.3)
    pg.screenshot(path=R + f'audio_{tag}_near_mm.png')
    res['near_mm_audio'] = A()
    pg.evaluate("window.__mm.zoom(true)"); time.sleep(0.5); pg.screenshot(path=R + f'audio_{tag}_zoom.png'); res['zoom_state'] = pg.evaluate("window.__mm.state()")
    pg.evaluate("window.__fx.setMode('day')"); time.sleep(1.0); pg.screenshot(path=R + f'audio_{tag}_day.png')
    pg.evaluate("window.__mm.zoom(false); window.__fx.setMode('night')")
    pg.evaluate("window.__walk.exit()"); time.sleep(1.0); pg.evaluate("window.__mm.draw()"); res['orbit_mm'] = pg.evaluate("window.__mm.state()"); pg.screenshot(path=R + f'audio_{tag}_orbit.png')
    res['art_state'] = pg.evaluate("window.__art.state()")
    b.close()
res['console'] = cons; res['net'] = net[:8]
print(json.dumps(res, ensure_ascii=False, indent=1))

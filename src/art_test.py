"""Playwright: lazy art loading. Counts network requests at start-up, then walks into W_IN3_L1 / W_OUT0_L1 and checks that
only nearby, in-view slots load (images via wsrv / same-origin proxy, video posters + HLS when < 8 m), E opens the info card."""
import json, math, time, sys, re
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/preview.html'
SH = '/workspace/outputs/cyber_louvre/renders/art/'
import os; os.makedirs(SH, exist_ok=True)
errors, reqs = [], []
def media_req(u): return not u.startswith('data:') and not re.search(r'(preview\.html|cdn\.jsdelivr\.net/npm/(three|three-mesh-bvh)@)', u)
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.on('request', lambda r: reqs.append((time.time(), r.url)))
    t0 = time.time(); pg.goto(URL)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    time.sleep(6)
    init = [u for t, u in reqs]
    out['initial_requests_total'] = len(init)
    out['initial_requests_art_media'] = [u[:90] for u in init if media_req(u)]
    out['state_initial'] = pg.evaluate('window.__art.state()')
    pg.evaluate("window.__fx.setMode('day')")
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    def look(x, y, z, yaw, wait, shot):
        n0 = len(reqs)
        pg.evaluate(f'(() => {{ window.__walk.setLook({yaw}, 0); window.__walk.setPos({x},{y},{z}); }})()')
        time.sleep(wait)
        st = pg.evaluate('window.__art.state()')
        new = [u for t, u in reqs[n0:] if media_req(u)]
        pg.screenshot(path=SH + shot + '.png', timeout=180000)
        return dict(state=st, new_media_requests=len(new), sample=[u[:100] for u in new[:8]])
    out['IN3_face_south'] = look(-58, 26, 0, math.pi, 20, 'in3_south')          # S012 image, S013 video
    out['IN3_face_north'] = look(-58, 25, 0, 0.0, 20, 'in3_north')               # S014-S015 videos
    out['OUT0_face_south'] = look(-70, -26, 0, math.pi, 20, 'out0_south')        # S016-S017 images
    out['OUT0_face_north'] = look(-70, -25, 0, 0.0, 20, 'out0_north')            # S018 image, S019 video
    out['IN3_video_close'] = look(-57, 30.5, 0, 0.0, 30, 'in3_video')             # S015 video at ~3 m -> HLS starts
    # info overlay
    look(-57, 30.5, 0, 0.0, 2, 'pre_info')
    pg.keyboard.press('KeyE'); time.sleep(0.8)
    out['info'] = pg.evaluate('window.__art.info()'); pg.screenshot(path=SH + 'info.png', timeout=180000); pg.keyboard.press('KeyE')
    # walk far away (other floor): everything near the W wing unloads
    out['far_away'] = look(0, 20, 0, 0.0, 5, 'lobby')
    pg.evaluate("window.__fx.setMode('night')"); time.sleep(1)
    out['night_back_in'] = look(-70, -25, 0, 0.0, 15, 'out0_north_night')
    out['art_log_count'] = len(pg.evaluate('window.__art.log()'))
    out['total_requests'] = len(reqs)
    out['console_errors'] = errors
    print(json.dumps(out, indent=1, ensure_ascii=False))
    json.dump(out, open(SH + 'art_test.json', 'w'), indent=1, ensure_ascii=False)
    b.close()

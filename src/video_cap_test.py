"""3-stream cap / priority test (cap lowered to 2 to make it deterministic): in NE_S1_L2 look east at S122 + S123 (both
stream), then turn west to S121 - the in-view video must get a stream (an out-of-view one is preempted), not stay a thumbnail.
Second check with the real cap 3: same room, stand close to S121 after the others played.  usage: video_cap_test.py URL"""
import sys, time, json
from playwright.sync_api import sync_playwright
url = sys.argv[1]; out = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 640, 'height': 360}); errs = []
    pg.on('console', lambda m: errs.append(m.text[:160]) if m.type == 'error' else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000)
    pg.evaluate('window.__art.cap(2)')
    pg.evaluate("window.__cam([34, 9.7, -34.2],[40.4, 9.6, -34.2],70)"); time.sleep(20)
    out['east'] = pg.evaluate('window.__art.videos()')
    pg.evaluate("window.__cam([34, 9.7, -36.1],[27.6, 9.6, -36.1],70)"); time.sleep(20)
    out['west'] = pg.evaluate('window.__art.videos()'); out['S121'] = pg.evaluate("window.__art.video('S121')"); out['preempted'] = pg.evaluate('window.__art.preempted()')
    pg.screenshot(path='/workspace/outputs/cyber_louvre/renders/art/video_cap_west.png')
    out['console'] = errs; b.close()
out['ok'] = any(v['slot'] == 'S121' for v in out['west']) and out['preempted'] >= 1
print(json.dumps(out, indent=1))

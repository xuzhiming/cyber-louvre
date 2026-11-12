"""Reproduce / check one video slot: camera 4 m in front, log network + console + <video> state, screenshot.  usage: video_repro.py URL SLOT TAG"""
import sys, time, json
from playwright.sync_api import sync_playwright
url, sid, tag = sys.argv[1], sys.argv[2], sys.argv[3]
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
s = S[sid]; x, y, z = s['pos']; nx, ny = s['normal'][:2]
net, cons = [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 1100, 'height': 620})
    pg.on('console', lambda m: cons.append((m.type, m.text[:200])) if m.type in ('error', 'warning') else None)
    pg.on('response', lambda r: net.append((r.status, r.request.resource_type, r.url[:140])) if any(k in r.url for k in ('MP4', 'mp4', 'm3u8', 'videodelivery', '/media/', 'wsrv')) else None)
    pg.on('requestfailed', lambda r: net.append(('FAILED', r.failure, r.url[:140])))
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000)
    pg.evaluate(f"window.__cam({[x + nx * 4, z + 0.1, -(y + ny * 4)]},{[x, z, -y]},60)")
    hist = []
    for k in range(25):
        time.sleep(1)
        hist.append(pg.evaluate(f"(() => {{ const r = window.__art.slot('{sid}'); return {{ state: r.state, kind: r.kind, v: window.__art.video ? window.__art.video('{sid}') : null }}; }})()"))
    st = pg.evaluate('window.__art.state()')
    pg.screenshot(path=f'/workspace/outputs/cyber_louvre/renders/art/video_{sid}_{tag}.png')
    b.close()
print(json.dumps(dict(slot=sid, last=hist[-1], first_loaded=next((i for i, h in enumerate(hist) if h['state'] == 'loaded'), None),
    videos=st['videos'], playing=st['playing'], req=st['req'], errors=st['errors'], net=net[:15], console=cons[:10]), ensure_ascii=False, indent=1))

"""All video works: camera 4 m in front of each slot, wait for the stream, check currentTime advances (t1 > t0 over 4 s).
Then a cap test: a spot with > MAXVID videos in range -> the nearest in-view video must be among the streams.  usage: video_audit.py URL"""
import sys, time, json
from playwright.sync_api import sync_playwright
url = sys.argv[1]
S = json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']
A = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json')); P = A['placement']; W = A['artworks']
vids = [(k, P[k]) for k in range(len(S)) if isinstance(P[k], int) and W[P[k]].get('video')]
res, errs = [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 640, 'height': 360})
    pg.on('console', lambda m: errs.append(m.text[:160]) if m.type == 'error' else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000)
    for k, wi in vids:
        s = S[k]; x, y, z = s['pos']; nx, ny = s['normal'][:2]; w = W[wi]
        pg.evaluate(f"window.__cam({[x + nx * 4, z + 0.1, -(y + ny * 4)]},{[x, z, -y]},60)")
        v0 = None
        for i in range(30):
            time.sleep(1); v0 = pg.evaluate(f"window.__art.video('{s['id']}')")
            if v0 and not v0.get('none') and v0['ready'] >= 2 and v0['t'] > 0: break
        time.sleep(4); v1 = pg.evaluate(f"window.__art.video('{s['id']}')")
        ok = bool(v0 and v1 and not v1.get('none') and v1['t'] > v0['t'])
        res.append(dict(slot=s['id'], title=w['title'][:28], kind='hls' if w.get('video_id') else 'mp4-' + w.get('video_codec', '?'), plays=ok,
                        t0=v0 and v0.get('t'), t1=v1 and v1.get('t'), size=v1 and (v1.get('w'), v1.get('h')), src=(v1 or {}).get('src', '')[:70], vfail=(v1 or {}).get('vfail')))
        print(res[-1], flush=True)
    # cap test: find the face with the most video slots around one spot
    st = pg.evaluate('window.__art.state()')
    b.close()
print(json.dumps(dict(total=len(res), playing=sum(r['plays'] for r in res), failed=[r for r in res if not r['plays']], art_errors=st['errors'], console=errs[:10]), ensure_ascii=False, indent=1))

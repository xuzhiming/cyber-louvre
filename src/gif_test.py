"""All animated works: put the camera 4 m in front of each slot, check it decodes + animates (frame counter advances),
no console errors; S032 screenshots (two moments) for the before/after sheet."""
import json, time, sys
from playwright.sync_api import sync_playwright
url, tag = sys.argv[1], sys.argv[2]
SH = '/workspace/outputs/cyber_louvre/renders/art/'
S = json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']
A = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json'))['artworks']
_P = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json')).get('placement')
if _P: S = {w: S[k] for k, w in enumerate(_P) if isinstance(w, int)}   # work index -> its slot (artist-grouped placement)
idx = [i for i, w in enumerate(A) if w.get('animated')]
errors, out = [], {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto(url)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate("window.__fx.setMode('day')")
    for i in idx:
        s = S[i]; x, y, z = s['pos']; nx, ny = s['normal'][:2]
        c = [x + nx * 4, 1.7 + z - 1.6, -(y + ny * 4)]; t = [x, z, -y]
        pg.evaluate(f"window.__cam({c},{t},60)")
        r0 = None
        for k in range(45):
            time.sleep(1); r0 = pg.evaluate(f"window.__art.slot('{s['id']}')")
            if r0 and r0['state'] in ('loaded', 'failed') and k > 3: break
        time.sleep(1); a = pg.evaluate(f"window.__art.slot('{s['id']}')")
        if A[i]['id'] == '1844383116844732416': pg.screenshot(path=SH + f'gif_{tag}_a.png', timeout=180000)
        time.sleep(4); bb = pg.evaluate(f"window.__art.slot('{s['id']}')")
        if A[i]['id'] == '1844383116844732416': pg.screenshot(path=SH + f'gif_{tag}_b.png', timeout=180000)
        out[s['id']] = dict(work=A[i]['title'][:24], state=bb['state'], kind=bb['kind'], anim=bb['anim'],
                            frames_advanced_in_4s=(bb['anim']['shown'] - a['anim']['shown']) if (a and a['anim'] and bb['anim']) else 0)
    # walk away -> decoders released
    pg.evaluate("window.__cam([0, 20, 200],[0, 10, 0],40)"); time.sleep(3)
    st = pg.evaluate('window.__art.state()')
    out['after_leaving'] = dict(anims=st['anims'], animating=st['animating'], loaded=st['loaded'], req=st['req'], imageDecoder=st['imageDecoder'], errors=st['errors'])
    out['console_errors'] = errors
    print(json.dumps(out, indent=1, ensure_ascii=False)); b.close()

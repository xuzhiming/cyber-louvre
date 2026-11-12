"""t36u: every bidder.top work displays (camera 3.5 m in front, orbit view): image/cover loaded (not failed), videos become
the single playing media and advance; info overlay links to bidder.top.  usage: top_works_test.py URL"""
import sys, time, json
from playwright.sync_api import sync_playwright
url = sys.argv[1]; R = '/workspace/outputs/cyber_louvre/renders/art/'
S = json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']
A = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json')); P = A['placement']; W = A['artworks']
todo = [(k, P[k]) for k in range(len(S)) if isinstance(P[k], int) and W[P[k]].get('source') == 'bidder.top']
res, cons, net = [], [], []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 900, 'height': 560})
    pg.on('console', lambda m: cons.append(m.text[:160]) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: cons.append('PAGEERROR ' + str(e)[:160]))
    pg.on('response', lambda r: net.append((r.status, r.url[:100])) if ('bidder.top' in r.url or '/media/top/' in r.url or 'thumbs/top_' in r.url) and r.status >= 400 else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    for n, (k, wi) in enumerate(todo):
        s = S[k]; x, y, z = s['pos']; nx, ny = s['normal'][:2]; w = W[wi]; sid = s['id']
        pg.evaluate(f"window.__cam({[x + nx * 3.5, z + 0.1, -(y + ny * 3.5)]},{[x, z, -y]},60)")
        st = None
        for i in range(40):
            time.sleep(0.5); st = pg.evaluate(f"window.__art.slot('{sid}')")
            if st['state'] in ('loaded', 'failed') and (w['media'] != 'video' or i > 6): break
        r = dict(slot=sid, id=w['id'], artist=w['artist'], media=w['media'], state=st['state'], kind=st['kind'])
        if w['media'] == 'video':
            v0 = None
            for i in range(40):
                time.sleep(0.5); v0 = pg.evaluate(f"window.__art.video('{sid}')")
                if v0 and not v0.get('none') and v0['t'] > 0.2: break
            time.sleep(2.5); v1 = pg.evaluate(f"window.__art.video('{sid}')"); m = pg.evaluate('window.__art.media()')
            r.update(plays=bool(v0 and v1 and not v1.get('none') and v1['t'] > v0['t']), cur=m['cur'], unpaused=m['unpaused'], has_audio=w.get('has_audio'), size=v1 and (v1.get('w'), v1.get('h')))
        pg.evaluate(f"window.__art.showSlot('{sid}')"); r['info_href'] = pg.evaluate('window.__art.info()')['href']; pg.evaluate('window.__art.hide()')
        if n in (0, 1, 9, 12, 13, 21): pg.screenshot(path=R + f'top_{sid}.png')
        res.append(r); print(r, flush=True)
    st = pg.evaluate('window.__art.state()')
    b.close()
ok = [r for r in res if r['state'] == 'loaded' and r['kind'] in ('image', 'video', 'anim') and (r['media'] != 'video' or r['plays']) and 'bidder.top/#/product/' in r['info_href']]
print(json.dumps(dict(total=len(res), ok=len(ok), failed=[r for r in res if r not in ok], art_errors=st['errors'], http_errors=net[:10], console=cons[:10]), ensure_ascii=False, indent=1))

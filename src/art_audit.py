"""Browser audit: visit every wall face that has works, record how each work ends up (image / anim / video / card / failed)."""
import json, time, sys, collections
from playwright.sync_api import sync_playwright
url = sys.argv[1]
S = json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']
A = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json'))['artworks']
_P = json.load(open('/workspace/outputs/cyber_louvre/web/artworks.json')).get('placement')
if _P: S = {w: S[k] for k, w in enumerate(_P) if isinstance(w, int)}   # work index -> its slot (artist-grouped placement)
faces = collections.OrderedDict()
for i, w in enumerate(A): faces.setdefault((S[i]['room'], S[i]['normal'][0], S[i]['normal'][1]), []).append(i)
res, errors = {}, []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto(url); pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    for key, ids in faces.items():
        ps = [S[i]['pos'] for i in ids]; x = sum(q[0] for q in ps) / len(ps); y = sum(q[1] for q in ps) / len(ps); z = ps[0][2]
        nx, ny = S[ids[0]]['normal'][:2]
        pg.evaluate(f"window.__cam({[x + nx * 5, z + 0.1, -(y + ny * 5)]},{[x, z, -y]},70)")
        for k in range(40):
            time.sleep(1)
            st = [pg.evaluate(f"window.__art.slot('{S[i]['id']}')") for i in ids]
            if all(s['state'] in ('loaded', 'failed') for s in st) and k > 2: break
        for i, s in zip(ids, st): res[i] = dict(slot=S[i]['id'], room=S[i]['room'], title=A[i]['title'][:30], media=A[i]['media'], state=s['state'], kind=s['kind'], src=(A[i].get('image') or '')[:60])
    errs = pg.evaluate('window.__art.state().errors')
    b.close()
c = collections.Counter((r['media'], r['kind'], r['state']) for r in res.values())
print(json.dumps(dict(summary={str(k): v for k, v in c.items()}, not_ok=[r for r in res.values() if r['kind'] in ('card', 'reserved') and r['media'] != 'text' or r['state'] != 'loaded'],
                      art_errors=errs, console_errors=errors[:10]), indent=1, ensure_ascii=False))
json.dump(res, open('/workspace/outputs/cyber_louvre/renders/art/audit.json', 'w'), ensure_ascii=False, indent=1)

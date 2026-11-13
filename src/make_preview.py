import base64, json
r = '/workspace/outputs/cyber_louvre/'
t = open(r + 'src/web_template.html').read()
g = base64.b64encode(open(r + 'web/model_web.glb', 'rb').read()).decode()
# artworks + slots inlined (works from file:// too); web/artworks.json + web/slots.json are published alongside
A = json.load(open(r + 'web/artworks.json'))
keep = ('id', 'title', 'artist', 'media', 'detail_url', 'price', 'edition', 'compilation', 'headline', 'quote', 'image', 'image_path',
        'video', 'video_id', 'thumbnail', 'width', 'height', 'aspect', 'animated', 'frames', 'poster_frame', 'local_thumb', 'video_path', 'video_codec', 'video_local', 'text', 'text_source')
keep = keep + ('artist_id', 'artist_url', 'audio', 'audio_path', 'audio_duration', 'has_audio', 'source', 'image_full', 'intro', 'tags', 'curator')
S = json.load(open(r + 'web/slots.json'))
import sys; sys.path.insert(0, r + 'src')
# ---- minimap plan data (t33u): per floor room rects + stair flights / landings from spec (walls are sliced from the model in the page)
import spec as SP
SP.build()
KC = {'gallery': 'g', 'platform': 'p', 'corridor': 'c', 'pavilion_hall': 'v', 'core_lobby': 'k', 'elevator': 'e', 'stair': 's', 'mech': 'm',
      'pyramid': 'y', 'concourse': 'b', 'hall': 'h', 'outdoor': 'o', 'lobby': 'l', 'atrium': 'a'}
LV = {'B1': (-6.0, 0.0), 'L1': (0.0, 8.0), 'L2': (8.0, 16.0), 'L3': (16.0, 24.0), 'L4': (24.0, 32.0)}
r1 = lambda v: round(float(v), 1)
plan = {k: dict(z=LV[k][0], sp=[], st=[]) for k in LV}
for sp in SP.SPACES.values():
    rects = sp.get('floor') or [sp['rect']]
    for b in sp.get('bands') or [sp['level']]:
        if b not in plan: continue
        for q in rects: plan[b]['sp'].append([r1(q[0]), r1(q[1]), r1(q[2]), r1(q[3]), KC.get(sp['kind'], 'g'), sp['id']])
for st in SP.STAIRS:
    for f in st['flights']:
        rs = [SP.flight_step_rect(f, i) for i in range(1, f['n'] + 1)]
        x0 = min(q[0][0] for q in rs); y0 = min(q[0][1] for q in rs); x1 = max(q[0][2] for q in rs); y1 = max(q[0][3] for q in rs)
        zl, zh = f['z0'], f['z0'] + f['n'] * f['riser']
        for b, (b0, b1) in LV.items():
            if zh >= b0 - 0.01 and zl < b1 - 0.01: plan[b]['st'].append([r1(x0), r1(y0), r1(x1), r1(y1), int(f['dx']), int(f['dy'])])
    for lr, z in st['landings']:
        for b, (b0, b1) in LV.items():
            if b0 - 0.01 <= z < b1 - 0.01: plan[b]['st'].append([r1(lr[0]), r1(lr[1]), r1(lr[2]), r1(lr[3]), 0, 0])
xs = [v for L in plan.values() for q in L['sp'] for v in (q[0], q[2])]; ys = [v for L in plan.values() for q in L['sp'] for v in (q[1], q[3])]
PLAN = dict(bounds=[min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3], levels=plan)

import sys; sys.path.insert(0, r + 'src')
from art_assign import place
placement, rep = place(A, S['slots'])
A['placement'] = placement; A['placement_report'] = rep          # kept in web/artworks.json too (published next to the page)
json.dump(A, open(r + 'web/artworks.json', 'w'), ensure_ascii=False, indent=1)
artists = [{k: a[k] for k in ('id', 'name', 'avatar', 'profile_url', 'n', 'works_total', 'source', 'bio') if a.get(k) not in (None, '')} for a in A['artists']]
art = dict(source=A['source'], count=A['count'], artworks=[{k: w[k] for k in keep if w.get(k) not in (None, '')} for w in A['artworks']],
           artists=artists, placement=placement)
if rep['overflow']: print('ART OVERFLOW (no free wall face):', rep['overflow'])
slots = dict(count=S['count'], slots=[{k: s[k] for k in ('id', 'room', 'band', 'pos', 'normal', 'size', 'inner')} for s in S['slots']])
js = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
out = t.replace('__ART_JSON__', js(art)).replace('__SLOTS_JSON__', js(slots)).replace('__PLAN_JSON__', js(PLAN)).replace('__GLB_BASE64__', g)
open(r + 'web/preview.html', 'w').write(out)
print(len(out))
